from flask import Flask, request
from flask_restx import Api, Resource
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import or_, and_
from marshmallow import Schema, fields


def check_keys(data: dict, allowed_keys: set) -> bool:
	"""Проверяет правильность ключей"""
	for key in data:
		if key not in allowed_keys:
			return False
	else:
		return True


app = Flask(__name__)
app.config['DEBUG'] = True
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True
app.config['JSON_AS_ASCII'] = False
app.config['RESTX_JSON'] = {'ensure_ascii': False, 'indent': 2}

db = SQLAlchemy(app)


# Создаем модели таблиц
class Movie(db.Model):
	__tablename__ = 'movie'
	id = db.Column(db.Integer, primary_key=True)
	title = db.Column(db.String(255))
	description = db.Column(db.String(255))
	trailer = db.Column(db.String(255))
	year = db.Column(db.Integer)
	rating = db.Column(db.Float)
	genre_id = db.Column(db.Integer, db.ForeignKey("genre.id"))
	genre = db.relationship("Genre")
	director_id = db.Column(db.Integer, db.ForeignKey("director.id"))
	director = db.relationship("Director")


class Director(db.Model):
	__tablename__ = 'director'
	id = db.Column(db.Integer, primary_key=True)
	name = db.Column(db.String(255))


class Genre(db.Model):
	__tablename__ = 'genre'
	id = db.Column(db.Integer, primary_key=True)
	name = db.Column(db.String(255))


# Создаем схемы для сериализации
class MovieSchema(Schema):
	id = fields.Int()
	title = fields.Str()
	description = fields.Str()
	trailer = fields.Str()
	year = fields.Int()
	rating = fields.Float()
	genre = fields.Str()
	director = fields.Str()


class DirectorSchema(Schema):
	id = fields.Int()
	name = fields.Str()


class GenreSchema(Schema):
	id = fields.Int()
	name = fields.Str()


# Создаем namespaces
api = Api(app)
movie_ns = api.namespace('movies')
director_ns = api.namespace('directors')
genre_ns = api.namespace('genres')

# Допустимые ключи для проверки
movie_keys = {'title', 'description', 'trailer', 'year', 'rating', 'genre_id', 'director_id'}
director_keys = {'name'}
genre_keys = {'name'}

# Создаем экземпляры классов схем сериализации
movie_s = MovieSchema()
movies_s = MovieSchema(many=True)
director_s = DirectorSchema()
directors_s = DirectorSchema(many=True)
genre_s = GenreSchema()
genres_s = GenreSchema(many=True)


# Представления для фильмов
@movie_ns.route('/')
class MoviesView(Resource):
	"""Вывод нескольких фильмов, добавление нового в БД"""
	def get(self):
		director_id = request.values.get('director_id')
		genre_id = request.values.get('genre_id')

		# Разделяем вывод фильмов на страницы
		try:
			page = int(request.values.get('page'))
			lim = int(request.values.get('limit'))
		except (TypeError, ValueError):
			page = 1
			lim = Movie.query.count()
		offs = (page - 1) * lim

		query_ = (
			Movie.id,
			Movie.title,
			Movie.description,
			Movie.trailer,
			Movie.year,
			Movie.rating,
			Director.name.label('director'),
			Genre.name.label('genre')
		)

		param = Movie.director_id == director_id, Movie.genre_id == genre_id
		if director_id and genre_id:
			movies = db.session.query(*query_).join(Director).join(Genre).filter(and_(*param)).all()
		elif director_id or genre_id:
			movies = db.session.query(*query_).join(Director).join(Genre).filter(or_(*param)).all()
		else:
			movies = db.session.query(*query_).join(Director).join(Genre).limit(lim).offset(offs).all()

		return movies_s.dump(movies), 200

	def post(self):
		data = request.json
		if not check_keys(data, movie_keys):
			return 'Переданы неверные ключи', 200
		db.session.add(Movie(**data))
		db.session.commit()
		return 'Фильм добавлен!', 200


@movie_ns.route('/<int:uid>')
class MovieView(Resource):
	"""Вывод, изменение, удаление одного фильма"""
	def get(self, uid):
		movie = Movie.query.get(uid)
		if not movie:
			return 'Нет фильма с таким ID', 404
		return movie_s.dump(movie), 200

	def put(self, uid):
		movie = Movie.query.get(uid)
		if not movie:
			return 'Нет фильма с таким ID', 404

		data = request.json
		if not check_keys(data, movie_keys):
			return 'Переданы неверные ключи', 200

		movie.title = data.get('title')
		movie.description = data.get('description')
		movie.trailer = data.get('trailer')
		movie.year = data.get('year')
		movie.rating = data.get('rating')
		movie.genre_id = data.get('genre_id')
		movie.director_id = data.get('director_id')

		db.session.add(movie)
		db.session.commit()
		return 'Данные фильма обновлены', 200

	def patch(self, uid):
		movie = Movie.query.get(uid)
		if not movie:
			return 'Нет фильма с таким ID', 404

		data = request.json
		if not check_keys(data, movie_keys):
			return 'Переданы неверные ключи', 200

		movie.title = data.get('title', movie.title)
		movie.description = data.get('description', movie.description)
		movie.trailer = data.get('trailer', movie.trailer)
		movie.year = data.get('year', movie.year)
		movie.rating = data.get('rating', movie.rating)
		movie.genre_id = data.get('genre_id', movie.genre_id)
		movie.director_id = data.get('director_id', movie.director_id)

		db.session.add(movie)
		db.session.commit()
		return 'Данные фильма обновлены', 200

	def delete(self, uid):
		movie = Movie.query.get(uid)
		if not movie:
			return 'Нет фильма с таким ID', 404
		db.session.delete(movie)
		db.session.commit()
		return 'Фильм удален', 200


# Представления для режиссеров
@director_ns.route('/')
class DirectorsView(Resource):
	"""Вывод всех режиссеров, добавление нового"""
	def get(self):
		directors = Director.query.all()
		return directors_s.dump(directors), 200

	def post(self):
		data = request.json
		if not check_keys(data, director_keys):
			return 'Переданы неверные ключи', 200

		db.session.add(Director(**data))
		db.session.commit()
		return 'Режиссер добавлен!', 201


@director_ns.route('/<int:uid>')
class DirectorView(Resource):
	"""Вывод, изменение, удаление режиссера"""
	def get(self, uid):
		director = Director.query.get(uid)
		if not director:
			return 'Нет режиссера с таким ID', 404
		return director_s.dump(director)

	def put(self, uid):
		director = Director.query.get(uid)
		if not director:
			return 'Нет режиссера с таким ID', 404

		data = request.json
		if not check_keys(data, director_keys):
			return 'Переданы неверные ключи', 200

		director.name = data.get('name')

		db.session.add(director)
		db.session.commit()
		return 'Данные режиссера обновлены', 200

	def delete(self, uid):
		director = Director.query.get(uid)
		if not director:
			return 'Нет режиссера с таким ID', 404
		db.session.delete(director)
		db.session.commit()
		return 'Режиссер удален', 200


# Представления для жанров
@genre_ns.route('/')
class GenresView(Resource):
	"""Вывод всех жанров, добавление нового"""
	def get(self):
		genres = Genre.query.all()
		return genres_s.dump(genres), 200

	def post(self):
		data = request.json
		if not check_keys(data, genre_keys):
			return 'Переданы неверные ключи', 200

		db.session.add(Genre(**data))
		db.session.commit()
		return 'Жанр добавлен!', 201


@genre_ns.route('/<int:uid>')
class GenreView(Resource):
	"""Вывод, изменение, удаление жанра"""
	def get(self, uid):
		genre = Genre.query.get(uid)
		if not genre:
			return 'Нет жанра с таким ID', 404
		return genre_s.dump(genre)

	def put(self, uid):
		genre = Genre.query.get(uid)
		if not genre:
			return 'Нет жанра с таким ID', 404

		data = request.json
		if not check_keys(data, genre_keys):
			return 'Переданы неверные ключи', 200

		genre.name = data.get('name')

		db.session.add(genre)
		db.session.commit()
		return 'Данные жанра обновлены', 200

	def delete(self, uid):
		genre = Genre.query.get(uid)
		if not genre:
			return 'Нет жанра с таким ID', 404
		db.session.delete(genre)
		db.session.commit()
		return 'Жанр удален', 200


if __name__ == '__main__':
	app.run()
