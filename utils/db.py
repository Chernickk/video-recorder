import datetime

from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Session
from sqlalchemy import create_engine


class DBConnect:
    def __init__(self, db_url, license_table):
        """prepare and automap db"""

        Base = automap_base()
        self._engine = create_engine(
            db_url,
            connect_args={"options": "-c timezone=utc"}
        )
        Base.prepare(self._engine, reflect=True)

        self._Car = Base.classes.car
        self.license_table = license_table
        self.Record = Base.classes.record
        self.RecordRequest = Base.classes.request
        self.GPS = Base.classes.gps

    def __enter__(self):
        self.session = Session(self._engine)
        self.car = self.session.query(self._Car).filter_by(license_table=self.license_table).first()

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.session.close()

    def add_record(self, filename, start_time, finish_time, pk=None):
        """ Добавить запись в базу данных """
        self.session.add(self.Record(file_name=filename,
                                     car=self.car,
                                     start_time=start_time,
                                     end_time=finish_time,
                                     request_id=pk))
        self.session.commit()

    def add_coordinates(self, coordinates: dict):
        """ Добавить координаты в базу данных """
        self.session.add(self.GPS(car=self.car,
                                  latitude=coordinates['latitude'],
                                  longitude=coordinates['longitude'],
                                  datetime=coordinates['datetime']))
        self.session.commit()

    def get_record_requests(self):
        query = self.session.query(self.RecordRequest).filter_by(delivered=False, car=self.car)

        results = [{
            'start_time': request.start_time,
            'finish_time': request.finish_time,
            'id': request.id,
        } for request in query]

        for request in query:
            request.delivered = True
        self.session.commit()

        return results

    def set_request_status(self, pk, status: bool):
        request = self.session.query(self.RecordRequest).filter_by(id=pk).first()

        request.record_status = status
        self.session.commit()

    def set_last_seen(self, ip_address):
        self.car.last_seen = datetime.datetime.now()
        self.car.ip_address = ip_address

        self.session.commit()

    def get_loading_status(self):
        return self.car.loading
