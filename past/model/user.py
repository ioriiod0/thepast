#-*- coding:utf-8 -*-

from MySQLdb import IntegrityError
from past.store import connect_db, connect_redis
from past.utils import randbytes

#-- connect db and redis
db_conn = connect_db()
redis_conn = connect_redis()

class User(object):
    
    def __init__(self, id):
        self.id = str(id)
        self.uid = None
        self.name = None
        self.session_id = None
    
    def __repr__(self):
        return "<User id=%s, name=%s, uid=%s, session_id=%s>" \
                % (self.id, self.name, self.uid, self.session_id)
    __str__ = __repr__

    @classmethod
    def get(cls, id):
        cursor = db_conn.cursor()
        cursor.execute("""select uid,name,session_id 
            from user where id=%s""", id)
        row = cursor.fetchone()
        cursor.close()
        if row:
            u = cls(id)
            u.uid = str(row[0])
            u.name = row[1]
            u.session_id = row[2]
            return u

        return None

    @classmethod
    def gets(cls, ids):
        return [cls.get(x) for x in ids]

    
    @classmethod
    def add(cls, name=None, uid=None, session_id=None):
        cursor = db_conn.cursor()
        user = None

        name = "" if name is None else name
        uid = "" if uid is None else uid
        session_id = session_id if session_id else randbytes(8)

        try:
            cursor.execute("""insert into user (uid, name, session_id) 
                values (%s, %s, %s)""", 
                (uid, name, session_id))
            user_id = cursor.lastrowid
            if uid == "":
                cursor.execute("""update user set uid=%s where id=%s""", 
                    (user_id, user_id))
            db_conn.commit()
            user = cls.get(user_id)
        except IntegrityError:
            db_conn.rollback()
        finally:
            cursor.close()

        return user

class UserAlias(object):

    def __init__(self, id_, type_, alias, user_id):
        self.id = id_
        self.type = type_
        self.alias = alias
        self.user_id = str(user_id)

    def __repr__(self):
        return "<UserAlias type=%s, alias=%s, user_id=%s>" \
                % (self.type, self.alias, self.user_id)
    __str__ = __repr__

    @classmethod
    def get(cls, type_, alias):
        ua = None
        cursor = db_conn.cursor()
        cursor.execute("""select id, user_id from user_alias 
                where `type`=%s and alias=%s""", 
                (type_, alias))
        row = cursor.fetchone()
        if row:
            ua = cls(row[0], type_, alias, row[1])
        cursor.close()

        return ua

    @classmethod
    def gets_by_user_id(cls, user_id):
        uas = []
        cursor = db_conn.cursor()
        cursor.execute("""select `id`, `type`, alias from user_alias 
                where user_id=%s""", user_id)
        rows = cursor.fetchall()
        if rows and len(rows) > 0:
            uas = [cls(row[0], row[1], row[2], user_id) for row in rows]
        cursor.close()

        return uas

    @classmethod
    def get_by_user_and_type(cls, user_id, type_):
        uas = cls.gets_by_user_id(user_id)
        for x in uas:
            if x.type == type_:
                return x
        return None

    @classmethod
    def bind_to_exists_user(cls, user, type_, alias):
        ua = cls.get(type_, alias)
        if ua:
            return None

        ua = None
        cursor = db_conn.cursor()
        try:
            cursor.execute("""insert into user_alias (`type`,alias,user_id) 
                    values (%s, %s, %s)""", (type_, alias, user.id))
            db_conn.commit()
            ua = cls.get(type_, alias)
        except IntegrityError:
            db_conn.rollback()
        finally:
            cursor.close()

        return ua

    @classmethod
    def create_new_user(cls, type_, alias, name=None):
        if cls.get(type_, alias):
            return None

        user = User.add(name)
        if not user:
            return None

        return cls.bind_to_exists_user(user, type_, alias)

class OAuth2Token(object):
   
    def __init__(self, alias_id, access_token, refresh_token):
        self.alias_id = alias_id
        self.access_token = access_token
        self.refresh_token = refresh_token

    @classmethod
    def get(cls, alias_id):
        ot = None
        cursor = db_conn.cursor()
        cursor.execute("""select access_token, refresh_token  
                from oauth2_token where alias_id=%s""", 
                (alias_id,))
        row = cursor.fetchone()
        if row:
            ot = cls(alias_id, row[0], row[1])

        return ot

    @classmethod
    def add(cls, alias_id, access_token, refresh_token):
        ot = None
        cursor = db_conn.cursor()
        try:
            cursor.execute("""replace into oauth2_token 
                    (alias_id, access_token, refresh_token)
                    values (%s, %s, %s)""", 
                    (alias_id, access_token, refresh_token))
            db_conn.commit()
            ot = cls.get(alias_id)
        except IntegrityError:
            db_conn.rollback()
        finally:
            cursor.close()

        return ot

        