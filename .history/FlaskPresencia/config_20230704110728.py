class Developement():
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///Database-Dev/database.db'
    SECRET_KEY = 'admin'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

class Developement2():
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///database_prueba2.db'
    SECRET_KEY = 'admin'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

class Developement3():
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///database_prueba3.db'
    SECRET_KEY = 'admin'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

class Production1():
    #utiliza sqlite
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = 'sqlite:///Database-Dev/database.db'
    SECRET_KEY = 'admin'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

class Production2():
    #utiliza mysql
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = 'mysql://root@localhost/flask'
    SECRET_KEY = 'admin'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

class Demo():
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///demo.db'
    SECRET_KEY = 'admin'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

class Demo2():
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///demo2.db'
    SECRET_KEY = 'admin'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

config = {
    'development': Developement,
    'production1': Production1,
    'production2': Production2,
    'development2': Developement2,
    'development3': Developement3,
    'demo': Demo,
    'demo2': Demo2
}