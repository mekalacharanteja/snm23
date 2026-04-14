from flask import Flask,request,redirect,url_for,render_template,flash,session,send_file
from flask_session import Session
from otp import genotp
from cmail import sendmail
from stoken import endata,dndata
import mysql.connector
from mysql.connector import (connection)
from io import BytesIO
import flask_excel as excel
from flask import jsonify
import re

# Database Connection
mydb = connection.MySQLConnection(
    user='root',
    password='Ramcharan@123',
    host='localhost',
    database='snmdb23',
    ssl_disabled=True   # ✅ ADD THIS LINE
)

app=Flask(__name__)
excel.init_excel(app)
app.config['SESSION_TYPE']='filesystem'
app.secret_key=b'\xdd\xb7\x8d/\xc8'
Session(app)


@app.route('/')
def home():
    return render_template('welcome.html')

# ---------------- REGISTER ----------------
@app.route('/register',methods=['GET','POST'])
def register():
    if request.method=='POST':
        username=request.form['username']
        useremail=request.form['useremail']
        userpassword=request.form['userpassword']
        try:
            cursor=mydb.cursor()
            cursor.execute('select count(useremail) from user where useremail=%s',[useremail])
            count_email=cursor.fetchone() #(0,) or (1,)
            print(count_email)
            cursor.close()
        except Exception as e:
            print(e)
            flash('Could verify email')
            return redirect(url_for('register'))
        else:
            if count_email[0]==0:
                gotp=genotp()
                userdata={'username':username,'useremail':useremail,'userpassword':userpassword,'serverotp':gotp}
                subject='User verification for SNM23 APP'
                body=f'Use the given OTP for SNM Verification {gotp}'
                sendmail(to=useremail,subject=subject,body=body)
                flash('OTP has been sent to given mail.')
                return redirect(url_for('otpverify',serverdata=endata(userdata)))
            elif count_email[0]==1:
                flash('Email already existed')
                return redirect(url_for('register'))
            else:
                flash('Could not sent otp')
    return render_template('register.html')

# ---------------- OTP VERIFY ----------------

@app.route('/otpverify/<serverdata>',methods=['GET','POST'])
def otpverify(serverdata):
    if request.method=='POST':
        userotp=request.form['userotp']
        try:
            dn_userdata=dndata(serverdata) #{'username':'anusha','useremail':'anusha@codegnan.com','userpassword':123,'serverotp':'D8bT6j'}
        except Exception as e:
            print(e)
            flash('could not verify OTP')
            return redirect(url_for('otpverify',serverdata=serverdata))
        else:
            if dn_userdata['serverotp']==userotp:
                #db connnection user details db store
                try:
                    cursor=mydb.cursor()
                    cursor.execute('insert into user(username,useremail,password) values(%s,%s,%s)',[dn_userdata['username'],dn_userdata['useremail'],dn_userdata['userpassword']])
                    mydb.commit()
                    cursor.close()                    
                except Exception as e:
                    print(e)
                    flash('Could not insert data')
                    return redirect(url_for('register'))
                else:
                    flash('Registration successfull')
                    return redirect(url_for('login'))
            else:
                flash('invalid otp')
                return redirect(url_for('otpverify',serverdata=serverdata))
    return render_template('otp.html',serverdata=serverdata)

# ---------------- LOGIN ----------------
@app.route('/login',methods=['GET','POST'])
def login():
    if request.method=='POST':
        login_useremail=request.form['useremail']
        login_password=request.form['userpassword']
        try:
            cursor=mydb.cursor(buffered=True)
            cursor.execute('select count(*) from user where useremail=%s',[login_useremail])
            email_count=cursor.fetchone() #(0,) or (1,)
            if email_count[0]==1:
                cursor.execute('select password from user where useremail=%s',[login_useremail])
                stored_password=cursor.fetchone() #(123,)
                cursor.close()
                if stored_password[0]==login_password:
                    session['user']=login_useremail
                    flash('Dashboard')
                    return redirect(url_for('dashboard'))
                else:
                    flash('Wrong password')
                    return redirect(url_for('login'))
            elif email_count[0]==0:
                flash('No email found')
                return redirect(url_for('login'))
            else:
                flash('could not verify user')
                return redirect(url_for('login'))
        except Exception as e:
            print(e)
            flash('Could not login')
            return redirect(url_for('login'))

    return render_template('login.html')

# ---------------- DASHBOARD ----------------
@app.route('/dashboard')
def dashboard():
    if session.get('user'):
        return render_template('dashboard.html')
    else:
        flash('pls login view dashboard')
        return redirect(url_for('login'))


# ---------------- ADD NOTES ----------------
@app.route('/addnotes', methods=['GET', 'POST'])
def addnotes():
    if not session.get('user'):
        return redirect(url_for('login'))

    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']

        cursor = mydb.cursor()
        cursor.execute('select userid from user where useremail=%s', [session['user']])
        user = cursor.fetchone()
        if user:
            cursor.execute(
                'insert into notes(title,content,added_by) values(%s,%s,%s)',
                [title, description, user[0]]
            )
            mydb.commit()

        cursor.close()
        flash('Note added')

    return render_template('addnotes.html')

#----------------VIEW ALL NOTES-------------------#

@app.route('/viewallnotes')
def viewallnotes():
    if session.get('user'):
        try:
            cursor=mydb.cursor(buffered=True)
            cursor.execute('select userid from user where useremail=%s',[session.get('user')])
            user=cursor.fetchone()
            if user:
                cursor.execute('select  notesid,title,created_at from notes where added_by=%s ',[user[0]])
                allnotesdata=cursor.fetchall() #[(1,'python','2026-03-31 9:53:10'),(2,'Mysql','2026-03-31 9:53:10')]
                cursor.close()
            else:
                flash('could not verify user')
                return redirect(url_for('dashboard'))
        except Exception as e:
            flash('could not get notes details')
            return redirect(url_for('dashboard'))
        else:
            return render_template('viewallnotes.html',allnotesdata=allnotesdata)
    else:
        flash('pls login to view all notes')
        return redirect(url_for('login'))
    
#--------------------VIEW NOTES-------------------#
@app.route('/viewnotes/<nid>')
def viewnotes(nid):
    if session.get('user'):
        try:
            cursor=mydb.cursor(buffered=True)
            cursor.execute('select userid from user where useremail=%s',[session.get('user')])
            user=cursor.fetchone()
            if user:
                cursor.execute('select  notesid,title,content,created_at from notes where added_by=%s and notesid=%s ',[user[0],nid])
                notesdata=cursor.fetchone() #(1,'python','2026-03-31 9:53:10')
                cursor.close()
            else:
                flash('could not verify user')
                return redirect(url_for('dashboard'))
        except Exception as e:
            flash('could not get notes details')
            return redirect(url_for('dashboard'))
        else:
            return render_template('viewnotes.html',notesdata=notesdata)
    else:
        flash('pls login to view all notes')
        return redirect(url_for('login'))

#----------------DELETE NOTES----------------#
@app.route('/deletenotes/<nid>')
def deletenotes(nid):
    if session.get('user'):
        try:
            cursor=mydb.cursor(buffered=True)
            cursor.execute('select userid from user where useremail=%s',[session.get('user')])
            user=cursor.fetchone()
            if user:
                cursor.execute('delete from notes where added_by=%s and notesid=%s ',[user[0],nid])
                mydb.commit()
                cursor.close()
            else:
                flash('could not verify user')
                return redirect(url_for('dashboard'))
        except Exception as e:
            flash('could not delete notes details')
            return redirect(url_for('dashboard'))
        else:
          flash('notes deleted successfully')
          return redirect(url_for('viewallnotes'))
    else:
        flash('pls login to view all notes')
        return redirect(url_for('login'))

#-----------UPDATE NOTES-------------#

@app.route('/updatenotes/<nid>',methods=["GET",'POST'])
def updatenotes(nid):
    if session.get('user'):
        try:
            cursor=mydb.cursor(buffered=True)
            cursor.execute('select userid from user where useremail=%s',[session.get('user')])
            user=cursor.fetchone()
            if user:
                cursor.execute('select  notesid,title,content,created_at from notes where added_by=%s and notesid=%s ',[user[0],nid])
                notesdata=cursor.fetchone() #(1,'python','2026-03-31 9:53:10')
                cursor.close()
            else:
                flash('could not verify user')
                return redirect(url_for('dashboard'))
        except Exception as e:
            flash('could not get notes details')
            return redirect(url_for('dashboard'))
        else:
            if request.method=='POST':
                updated_title=request.form['title']
                updated_content=request.form['description']
                try:
                    cursor=mydb.cursor(buffered=True)
                    cursor.execute('select userid from user where useremail=%s',[session.get('user')])
                    user=cursor.fetchone() #(2,)
                    if user:
                        cursor.execute('update notes set title=%s ,content=%s where added_by=%s and notesid=%s',[updated_title,updated_content,user[0],nid])
                        mydb.commit()
                        cursor.close()
                    else:
                        flash('could not verify user')
                        return redirect(url_for('dashboard'))
                except Exception as e:
                    print(e)
                    flash('Could not update notes details')
                    return redirect(url_for('viewallnotes'))
                else:
                    flash(f'Notes {updated_title} updated successfully')
                    return redirect(url_for('viewnotes',nid=nid))
            return render_template('updatenotes.html',notesdata=notesdata)
    else:
        flash('pls login to view all notes')
        return redirect(url_for('login'))

# ---------------- FILE UPLOAD FIX ----------------#

@app.route('/uploadfile', methods=['GET', 'POST'])
def uploadfile():
    if not session.get('user'):
        return redirect(url_for('login'))

    if request.method == 'POST':
        file = request.files['file']
        cursor = mydb.cursor()

        # ✅ FIXED HERE
        cursor.execute('select userid from user where useremail=%s', [session['user']])
        user = cursor.fetchone()

        if user:
            cursor.execute(
                'insert into files(filename,filedata,added_by) values(%s,%s,%s)',
                [file.filename, file.read(), user[0]]
            )
            mydb.commit()

        cursor.close()
        flash('File uploaded')

    return render_template('fileupload.html')


#----------------------ALL FILE DATA-------------------------#


@app.route('/allfilesdata')
def allfilesdata():
    if session.get('user'):
        try:
            cursor=mydb.cursor(buffered=True)
            cursor.execute('select userid from user where useremail=%s',[session.get('user')])
            user=cursor.fetchone()
            if user:
                cursor.execute('select  filesid,filename,created_at from files where added_by=%s ',[user[0]])
                allfilesdata=cursor.fetchall() #[(1,'otp.py','2026-2-23'),(2,'cmail.py','2025-09-23')]
                cursor.close()
            else:
                flash('could not verify user')
                return redirect(url_for('dashboard'))
        except Exception as e:
            flash('could not get file details')
            return redirect(url_for('dashboard'))
        else:
            return render_template('viewallfiles.html',allfilesdata=allfilesdata)
    else:
        flash('pls login to view all files')
        return redirect(url_for('login'))

#----------------------VIEW FILE DATA-------------------#

@app.route('/viewfiledata/<fid>')
def viewfiledata(fid):
    if session.get('user'):
        try:
            cursor=mydb.cursor(buffered=True)
            cursor.execute('select userid from user where useremail=%s',[session.get('user')])
            user=cursor.fetchone()
            if user:
                cursor.execute('select  filesid,filename,filedata,created_at from files where added_by=%s and filesid=%s',[user[0],fid])
                stored_filedata=cursor.fetchone() #[(1,'otp.py','2026-2-23')
                cursor.close()
            else:
                flash('could not verify user')
                return redirect(url_for('dashboard'))
        except Exception as e:
            flash('could not get file details')
            return redirect(url_for('dashboard'))
        else:
            array_data=BytesIO(stored_filedata[2])
            return send_file(array_data,as_attachment=False,download_name=stored_filedata[1])
    else:
        flash('pls login to viewfiles')
        return redirect(url_for('login'))


#------------------------DOWNLOAD FILE------------------------#
@app.route('/downloadfiledata/<fid>')
def downloadfiledata(fid):
    if session.get('user'):
        try:
            cursor=mydb.cursor(buffered=True)
            cursor.execute('select userid from user where useremail=%s',[session.get('user')])
            user=cursor.fetchone()
            if user:
                cursor.execute('select  filesid,filename,filedata,created_at from files where added_by=%s and filesid=%s',[user[0],fid])
                stored_filedata=cursor.fetchone()
                print(stored_filedata) #[(1,'otp.py','2026-2-23')
                cursor.close()
            else:
                flash('could not verify user')
                return redirect(url_for('dashboard'))
        except Exception as e:
            flash('could not get file details')
            return redirect(url_for('dashboard'))
        else:
            array_data=BytesIO(stored_filedata[2])
            return send_file(array_data,as_attachment=True,download_name=stored_filedata[1])
    else:
        flash('pls login to downloadfiles')
        return redirect(url_for('login'))

#------------------------DELETE FILE ------------------------#

@app.route('/deletefile/<fid>')
def deletefile(fid):
    if session.get('user'):
        try:
            cursor=mydb.cursor(buffered=True)
            cursor.execute('select userid from user where useremail=%s',[session.get('user')])
            user=cursor.fetchone()
            if user:
                cursor.execute('delete from files where added_by=%s and filesid=%s ',[user[0],fid])
                mydb.commit()
                cursor.close()
            else:
                flash('could not verify user')
                return redirect(url_for('dashboard'))
        except Exception as e:
            flash('could not delete file details')
            return redirect(url_for('allfilesdata'))
        else:
          flash('file deleted successfully')
          return redirect(url_for('allfilesdata'))
    else:
        flash('pls login delete file')
        return redirect(url_for('login'))

# ---------------- LOGOUT ----------------

@app.route('/logout')
def logout():
    if session.get('user'):
        session.pop('user')
        return redirect(url_for('login'))
    else:
        flash('pls login to logout')
        return redirect(url_for('login'))


@app.route('/getexceldata')
def getexceldata():
    if session.get('user'):
        try:
            cursor=mydb.cursor(buffered=True)
            cursor.execute('select userid from user where useremail=%s',[session.get('user')])
            user=cursor.fetchone()
            if user:
                cursor.execute('select  notesid,title,content,created_at from notes where added_by=%s ',[user[0]])
                allnotesdata=cursor.fetchall() #[(1,'python','2026-03-31 9:53:10'),(2,'Mysql','2026-03-31 9:53:10')]
                cursor.close()
            else:
                flash('could not verify user')
                return redirect(url_for('dashboard'))
        except Exception as e:
            flash('could not get notes details')
            return redirect(url_for('dashboard'))
        else:
            columns=['Notesid','Title','Content','Date']
            array_data=[list(i) for i in allnotesdata]
            array_data.insert(0,columns)
            return excel.make_response_from_array(array_data,'xlsx',file_name='data.xlsx')
    else:
        flash('pls login to getexcel')
        return redirect(url_for('login'))

@app.route('/search',methods=['POST'])
def search():
    if session.get('user'):
        sdata=request.form['searchdata']
        strg=['a-zA-Z0-9']
        pattern=re.compile(f'^{strg}',re.IGNORECASE)
        if pattern.match(sdata):
            try:
                cursor=mydb.cursor(buffered=True)
                cursor.execute('select userid from user where useremail=%s',[session.get('user')])
                user=cursor.fetchone()
                if user:
                    cursor.execute('select  notesid,title,content,created_at from notes where added_by=%s and (title like %s or content like %s or created_at like %s)',[user[0],sdata+'%',sdata+'%',sdata+'%'])
                    searchnotesdata=cursor.fetchall() #[(1,'python','2026-03-31 9:53:10'),(2,'Mysql','2026-03-31 9:53:10')]
                    cursor.close()
                else:
                    flash('could not verify user')
                    return redirect(url_for('dashboard'))
            except Exception as e:
                flash('could not get notes details')
                return redirect(url_for('dashboard'))
            else:
                return render_template('viewallnotes.html',allnotesdata=searchnotesdata)      
        else:
            flash('Invalid search data')
            return redirect(url_for('dashboard'))

    else:
        flash("pls login to search data")
        return redirect(url_for('login'))
    
#---------------FORGOT PASSWORD-------------------#
@app.route('/forgot',methods=['GET','POST'])
def forgot():
    if request.method=='POST':
        useremail=request.form['useremail']
        try:
            cursor=mydb.cursor()
            cursor.execute('select count(useremail) from user where useremail=%s',[useremail])
            count_email=cursor.fetchone()
            print(count_email)
            cursor.close()
        except Exception as e:
            print(e)
            flash('could verify email')
            return redirect(url_for('login'))
        else:
            if count_email[0]==1:
                subject='Forgot password link for SNM23 APP'
                body=f"Use the given link for SNM Forgotpassword {url_for('newpassword',data=endata(useremail),_external=True)}"
                sendmail(to=useremail,subject=subject,body=body)
                flash('Resetlink has been sent to the given mail')
                return redirect(url_for('forgot'))
            elif count_email[0]==0:
                flash('Email not found')
                return redirect(url_for('login'))
            else:
                flash('Could not send restlink')
    return render_template('forgot.html')



@app.route('/newpassword/<data>',methods=['GET','PUT'])
def newpassword(data):
    if request.method=='PUT':
        try:
            useremail=dndata(data)
        except Exception as e:
            print(e)
            flash('could not find user')
            return redirect(url_for('newpassword',data=data))
        else:
            print(request.get_json())
            updated_password=request.get_json()['password']
            try:
                cursor=mydb.cursor(buffered=True)
                cursor.execute('update user set password=%s where useremail=%s',[updated_password,useremail])
                mydb.commit()
                cursor.close()
            except Exception as e:
                print(e)
                flash('Could not update the password')
                return redirect(url_for('newpassword',data=data))
            else:
                flash('password updated sucessfully')
                return jsonify({"message":"ok"})
    return render_template('newpassword.html',data=data)

# ---------------- RUN ----------------
app.run(debug=True,use_reloader=True)