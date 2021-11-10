from datetime import datetime

from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Session
from sqlalchemy import create_engine


class DBConnect:
    def __init__(self, db_url, car_id):
        """prepare and automap db"""

        Base = automap_base()
        self._engine = create_engine(
            db_url,
            connect_args={"options": "-c timezone=utc"}
        )
        Base.prepare(self._engine, reflect=True)

        self._Car = Base.classes.car
        self.car_id = car_id
        self.Record = Base.classes.record
        self.GPS = Base.classes.gps

    def __enter__(self):
        self.session = Session(self._engine)
        self.car = self.session.query(self._Car).filter_by(id=self.car_id).first()

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.session.close()

    def add_record(self, filename):
        """ Добавить запись в базу данных """
        datetime_formatted = datetime.strptime(filename[:19], '%Y-%m-%d_%H:%M:%S')
        self.session.add(self.Record(file_name=filename,
                                     car=self.car,
                                     start_time=datetime_formatted))
        self.session.commit()

    def add_coordinates(self, coordinates: dict):
        """ Добавить координаты в базу данных """
        self.session.add(self.GPS(car=self.car,
                                  latitude=coordinates['latitude'],
                                  longitude=coordinates['longitude'],
                                  datetime=coordinates['datetime']))
        self.session.commit()