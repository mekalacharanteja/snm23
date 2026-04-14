from itsdangerous import URLSafeTimedSerializer
salt='Code8989'
secret_key='snm8989'
def endata(data):
    serializer=URLSafeTimedSerializer(secret_key)
    return serializer.dumps(data,salt=salt)
def dndata(data):
    serializer=URLSafeTimedSerializer(secret_key)
    return serializer.loads(data,salt=salt,max_age=60)
