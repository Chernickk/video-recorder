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

    def add_record(self, filename, video_duration):
        datetime_formatted = datetime.strptime(filename[:19], '%Y-%m-%d_%H:%M:%S')
        end_time = datetime_formatted + video_duration
        self.session.add(self.Record(file_name=filename,
                                     is_deleted=False,
                                     car=self.car,
                                     start_time=datetime_formatted,
                                     end_time=end_time))
        self.session.commit()

    def add_coordinates(self, coordinates: dict):

        self.session.add(self.GPS(car=self.car,
                                  latitude=coordinates['latitude'],
                                  longitude=coordinates['longitude'],
                                  datetime=coordinates['datetime']))
        self.session.commit()
