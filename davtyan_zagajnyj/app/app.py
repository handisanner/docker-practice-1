import os
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

DB_USER = os.environ.get("DB_USER", "postgres")
DB_PASS = os.environ.get("DB_PASS", "postgres")
DB_HOST = os.environ.get("DB_HOST", "db")
DB_PORT = os.environ.get("DB_PORT", "5432")
DB_NAME = os.environ.get("DB_NAME", "images_db")

app.config["SQLALCHEMY_DATABASE_URI"] = (
    f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

image_tags = db.Table(
    "image_tags",
    db.Column("image_id", db.Integer, db.ForeignKey("image.id"), primary_key=True),
    db.Column("tag_id", db.Integer, db.ForeignKey("tag.id"), primary_key=True),
)


class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)


class Image(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String(2048), nullable=False)
    width = db.Column(db.Integer, nullable=False)
    height = db.Column(db.Integer, nullable=False)
    tags = db.relationship("Tag", secondary=image_tags, backref="images", lazy="joined")

    def to_dict(self):
        return {
            "id": self.id,
            "url": self.url,
            "width": self.width,
            "height": self.height,
            "tags": [t.name for t in self.tags],
        }

with app.app_context():
    db.create_all()

@app.route("/images", methods=["GET"])
def get_images():
    """
    GET /images          — все изображения
    GET /images?tag=xxx  — фильтрация по тегу
    """
    tag_filter = request.args.get("tag")

    if tag_filter:
        # Ищем изображения, у которых есть тег с заданным именем
        images = Image.query.filter(Image.tags.any(Tag.name == tag_filter)).all()
    else:
        images = Image.query.all()

    return jsonify([img.to_dict() for img in images]), 200


@app.route("/images/<int:image_id>", methods=["GET"])
def get_image(image_id):
    """GET /images/{id} — детали одного изображения."""
    image = db.session.get(Image, image_id)
    if image is None:
        return jsonify({"error": "Image not found"}), 404
    return jsonify(image.to_dict()), 200


@app.route("/images", methods=["POST"])
def create_image():
    """
    POST /images
    Body: {"url":"...","width":800,"height":600,"tags":["landscape"]}
    """
    data = request.get_json(silent=True)

    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    url = data.get("url")
    width = data.get("width")
    height = data.get("height")
    tag_names = data.get("tags", [])

    if not url or width is None or height is None:
        return jsonify({"error": "Fields 'url', 'width', 'height' are required"}), 400

    tag_objects = []
    for name in tag_names:
        tag = Tag.query.filter_by(name=name).first()
        if tag is None:
            tag = Tag(name=name)
            db.session.add(tag)
        tag_objects.append(tag)

    image = Image(url=url, width=width, height=height, tags=tag_objects)
    db.session.add(image)
    db.session.commit()

    return jsonify(image.to_dict()), 201


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)