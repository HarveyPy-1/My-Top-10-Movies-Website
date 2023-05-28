from flask import Flask, render_template, redirect, url_for, request
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired
import requests
import secrets
import json

# -------------------------------------- CONSTANT VARIABLES ----------------------------------- #
API_KEY = 'f87ce795918228265ec8235c5a44dff7'
API_READ_ACCESS_TOKEN = 'eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiJmODdjZTc5NTkxODIyODI2NWVjODIzNWM1YTQ0ZGZmNyIsInN1YiI6IjY0Nz' \
                        'I0ZGI0ODgxM2U0MDEwMzU3MjI4MCIsInNjb3BlcyI6WyJhcGlfcmVhZCJdLCJ2ZXJzaW9uIjoxfQ.eUCnfyXLXbbTT' \
                        'JgCZnTd8LiMO8u6snbMVLgSVI3gCIY'

URL = 'https://api.themoviedb.org/3/search/movie'
IMAGE_URL_PREFIX = 'https://image.tmdb.org/t/p/w500'


# -------------------------------------- CREATE FLASK AND BOOTSTRAP OBJECTS ----------------------------------- #
secret = secrets.token_hex(16)

app = Flask(__name__)
app.config['SECRET_KEY'] = secret
Bootstrap(app)


# -------------------------------------- INITIALIZE DATABASE ----------------------------------- #
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///movies_collection.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


# -------------------------------------- CREATE SCHEMA ----------------------------------- #
class Movies(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(250), unique=True, nullable=False)
    year = db.Column(db.Integer, unique=False, nullable=False)
    description = db.Column(db.String(500), unique=False, nullable=False)
    rating = db.Column(db.Float(250), unique=False, nullable=True)
    ranking = db.Column(db.Integer, unique=False, nullable=True)
    review = db.Column(db.String(500), unique=False, nullable=True)
    img_url = db.Column(db.String(500), unique=False, nullable=False)

    def __repr__(self):
        return f'<Movie: {self.title}>'


# -------------------------------- CREATE REQUIRED FORMS USING FLASK/BOOTSTRAP WTFORMS ----------------------------- #
class MovieForm(FlaskForm):
    update_rating = StringField('New rating out of 10 (e.g. 7.5)', validators=[DataRequired()])
    update_review = StringField('New review', validators=[DataRequired()])
    submit = SubmitField('Done')


class AddMovieForm(FlaskForm):
    add_movie = StringField('Movie Title', validators=[DataRequired()])
    submit = SubmitField('Add Movie')


# -------------------------------------- DEFINE ALL WEBPAGES ----------------------------------- #
@app.route("/")
def home():
    """Queries the database for all movies, puts it into a list, sorts the list according to rating and ranks
    accordingly. It displays in index.html"""
    # QUERY DATABASE TO GET ALL MOVIES AND APPEND TO LIST
    with app.app_context():
        db.create_all()
        movies = Movies.query.all()
        movies_list = []
        for movie in movies:
            movie_data = {
                'id': movie.id,
                'title': movie.title,
                'year': movie.year,
                'description': movie.description,
                'rating': movie.rating,
                'ranking': movie.ranking,
                'review': movie.review,
                'img_url': movie.img_url
            }
            movies_list.append(movie_data)

        # SORT LIST ACCORDING TO RATING AND RANK ACCORDINGLY
        sorted_list = sorted(movies_list, key=lambda x: x['rating'], reverse=True)
        for i, item in enumerate(sorted_list):
            item['ranking'] = i + 1
    return render_template("index.html", all_movies=sorted_list)


@app.route('/edit', methods=['GET', 'POST'])
def edit():
    """Updates the rating and review of a movie"""
    # DEPLOY FORM FROM PREVIOUSLY CREATED FORMS
    form = MovieForm()
    if request.method == 'POST':
        if form.validate_on_submit():
            with app.app_context():
                db.create_all()
                movie_id = request.args.get('id')
                movie_to_update = db.session.get(Movies, movie_id)
                movie_to_update.rating = form.update_rating.data
                movie_to_update.review = form.update_review.data
                db.session.commit()
                return redirect(url_for('home'))
    movie_id = request.args.get('id')
    chosen_movie = db.session.get(Movies, movie_id)
    return render_template('edit.html', form=form, chosen_movie=chosen_movie)


@app.route('/delete')
def delete():
    """Deletes entire row of a selected movie entry"""
    with app.app_context():
        db.create_all()
        movie_id = request.args.get('id')
        movie_to_delete = db.session.get(Movies, movie_id)
        db.session.delete(movie_to_delete)
        db.session.commit()
        return redirect(url_for('home'))


@app.route("/confirm")
def confirm():
    """Confirm delete request"""
    with app.app_context():
        db.create_all()
        movie_id = request.args.get('id')
        movie_to_delete = db.session.get(Movies, movie_id)
        return render_template("confirm.html", movie=movie_to_delete)


@app.route('/add', methods=['GET', 'POST'])
def add():
    """Add new movie to the database"""
    # DEPLOY FORM FROM PREVIOUSLY CREATED FORM
    form = AddMovieForm()
    if request.method == 'POST':
        if form.validate_on_submit():

            # MAKE REQUEST TO EXTERNAL API TO GET MOVIE SEARCH RESULTS
            headers = {
                "accept": "application/json",
                "Authorization": f"Bearer {API_READ_ACCESS_TOKEN}"
            }

            parameters = {
                'query': form.add_movie.data,
                'include_adult': True,
                'language': 'en-US',
                'page': 1
            }
            response = requests.get(URL, params=parameters, headers=headers)
            data = response.text

            json_data = json.loads(data)
            results = json_data['results']

            return render_template('select.html', data=results)  # Even with this, it still shows /add. Because you
            # don't create any '/select route or function for it.. Interesting
    return render_template('add.html', form=form)


@app.route('/find')  # You can even create whole ass functions that just redirect to home
def find_movie():
    """Accepts a particular movie choice from the list gotten in the 'add' function, finds it's details from the
    external API and adds relevant information to the database"""
    movie_id = request.args.get('id')
    if movie_id:

        headers = {
            "accept": "application/json",
            "Authorization": f"Bearer {API_READ_ACCESS_TOKEN}"
        }

        response = requests.get(f'https://api.themoviedb.org/3/movie/{movie_id}?language=en-US', headers=headers)
        json_data = json.loads(response.text)

        with app.app_context():
            db.create_all()
            new_movie = Movies(
                title=json_data['original_title'],
                year=json_data['release_date'].split('-')[0],
                img_url=f'{IMAGE_URL_PREFIX}{json_data["poster_path"]}',
                description=json_data['overview']
            )
            db.session.add(new_movie)
            db.session.commit()

        with app.app_context():
            db.create_all()
            get_movie = Movies.query.filter_by(title=json_data['original_title']).first()
            return redirect(url_for('edit', id=get_movie.id))


# -------------------------------------- RUN FLASK ----------------------------------- #
if __name__ == '__main__':
    app.run(debug=True)
