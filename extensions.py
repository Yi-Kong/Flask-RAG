from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

# flask --app run db init
# flask --app run db migrate
# flask --app run db upgrade 
db = SQLAlchemy()
migrate = Migrate()