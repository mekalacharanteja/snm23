import random
def genotp():
    u_1=[chr(i) for i in range(ord('A'),ord('Z')+1)]
    s_1=[chr(i) for i in range (ord('a'),ord('z')+1)]
    otp=''
    for i in range(2):
        otp=otp+random.choice(u_1)+str(random.randint(0,9))+random.choice(s_1)
    return otp