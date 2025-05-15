## Set Up Starter

1. Git clone repository

```python
git clone https://github.com/charmandercodes/django-starter.git . && rm -rf .git
```

1. Create virtual environment to keep environment isolated on machine

```python
python3 -m venv venv
```

```python
source venv/bin/activate
```

1. upgrade pip

```python
pip install --upgrade pip 
```

1. Install requirements.txt

```python
pip install -r requirements.txt 
```

1. migrate the database

```python
python manage.py migrate
```

1. Create admin user

```python
python manage.py createsuperuser
```

1. Run server

```python
python manage.py runserver
```
