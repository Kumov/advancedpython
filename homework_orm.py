import mysql.connector

class Field:
    def __init__(self, f_type, required=True, default=None):
        self.f_type = f_type
        self.required = required
        self.default = default

    def validate(self, value):
        if value is None and not self.required:
            return None

        # TODO exceptions
        # compare f_type и value
        # f_type == type(value)

        return self.f_type(value)


class IntField(Field):
    def __init__(self, required=True, default=None):
        super().__init__(int, required, default)


class StringField(Field):
    def __init__(self, required=True, default=None):
        super().__init__(str, required, default)


class Manage:
    def __init__(self):
        self.model_cls = None

    def __get__(self, instance, owner):
        if self.model_cls is None:
            self.model_cls = owner
        return self
    
    def where(self, **kwargs):
        self.params = kwargs.values()
        equations = [key + ' = %s' for key in kwargs.keys()]
        self.where_expr = 'WHERE ' + ' AND '.join(equations) if len(equations) > 0 else ''
        return self

    def update(self, **kwargs):
        _keys = []
        _params = []

        for field_name, field in self.model_cls._fields.items():
            if kwargs.get(field_name) is not None:
                value = field.validate(kwargs.get(field_name))
                setattr(self.model_cls, field_name, value)
                _keys.append(field_name)
                _params.append(value)

        _params.extend(self.params)
        sql = 'UPDATE %s SET %s %s' % (
            self.model_cls.Meta.table_name, ', '.join([key + ' = %s' for key in _keys]), self.where_expr)
        return Database.execute(sql, _params)

    def delete(self):
        sql = 'DELETE FROM %s %s' % (
            self.model_cls.Meta.table_name, self.where_expr)
        return Database.execute(sql, list(self.params))

    def select(self):
        sql = 'SELECT %s FROM %s %s' % (', '.join(self.model_cls._fields.keys()), self.model_cls.Meta.table_name, self.where_expr)
        for row in Database.execute(sql, list(self.params)).fetchall():
            dict_with_values = {}

            for idx, f in enumerate(row):
                dict_with_values[list(self.model_cls._fields.keys())[idx]] = f

            inst = self.model_cls(**dict_with_values)

            yield inst


class ModelMeta(type):
    def __new__(mcs, name, bases, namespace):
        if name == 'Model':
            return super().__new__(mcs, name, bases, namespace)

        meta = namespace.get('Meta')
        if meta is None:
            raise ValueError('meta is none')
        if not hasattr(meta, 'table_name'):
            raise ValueError('table_name is empty')

        # todo mro
        for base in bases:
            namespace.update(base.__dict__.get('_fields', []))

        fields = {k: v for k, v in namespace.items()
                  if isinstance(v, Field)}
        namespace['_fields'] = fields
        namespace['_table_name'] = meta.table_name
        return super().__new__(mcs, name, bases, namespace)


class Model(metaclass=ModelMeta):
    class Meta:
        table_name = ''

    objects = Manage()
    # todo DoesNotExist


    def __init__(self, *_, **kwargs):
        for field_name, field in self._fields.items():
            value = field.validate(kwargs.get(field_name))
            setattr(self, field_name, value)

    def save(self):
        stmt = "SHOW TABLES LIKE " + '\'' + self.Meta.table_name + '\''
        result = Database.execute(stmt).fetchone()
        # check that table exists
        if not result:
            stmt = 'CREATE TABLE {table_name} ({fields})'

            def map_field_type(t):
                if t == int:
                    return 'INT'

                if t == str:
                    return 'TEXT'

            def make_fields_stmt(meta_fields):
                fields = []
                for k, v in meta_fields.items():
                    f_type = map_field_type(v)
                    fields.append('{f_name} {f_type}'.format(f_name=k, f_type=f_type))
                return ','.join(fields)

            user_meta_fields = {}
            
            for attr_name, attr_value in self.__dict__.items():
                user_meta_fields[attr_name] = type(attr_value)

            fields = make_fields_stmt(user_meta_fields)
            create_table = stmt.format(table_name=self.Meta.table_name, fields=fields)

            Database.execute(create_table)


        insert = 'INSERT INTO %s (%s) VALUES (%s)' % (
            self.Meta.table_name, ', '.join(self.__dict__.keys()), ', '.join(['%s'] * len(self.__dict__)))
        return Database.execute(insert, list(self.__dict__.values()))


class Database(object):
    autocommit = True
    conn = None
    db_config = {}

    @classmethod
    def connect(cls, **db_config):
        cls.conn = mysql.connector.connect(host=db_config.get('host', 'localhost'),
                                   user=db_config.get('user', 'root'), password=db_config.get('password', '1234'),
                                   database=db_config.get('database', 'new_schema_test'))

        cls.conn.autocommit = cls.autocommit
        cls.db_config.update(db_config)

    @classmethod
    def execute(cls, *args):
        cursor = cls.conn.cursor()
        cursor.execute(*args)
        return cursor


class User(Model):
    id = IntField()
    name = StringField()

    class Meta:
        table_name = 'Table_User'


class Man(User):
    sex = StringField()

    class Meta:
        table_name = 'Table_Man'


db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '1234',
    'database': 'new_schema_test'
}

Database.connect(**db_config)


man = Man(id=1, name='Ivan', sex='male')
man.save()


user = User(id=1, name='name1')
user.save()

user.id = 2
user.name = 'name2'
user.save()

user.id = 3
user.name = 'name3'
user.save()

user.id = 4
user.name = 'name1'
user.save()


User.objects.where(id=3, name='name3').update(id=6)


for r in User.objects.where(name='name1').select():
  print(r.id)
  print(r.name)


User.objects.where(id=2, name='name2').delete()
