from datetime import datetime

from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Session
from sqlalchemy import create_engine


class DBConnect:
    def __init__(self, db_url, car_id):
        """prepare and automap db"""

        Base = automap_base()
        engine = create_engine(
            db_url,
            connect_args={"options": "-c timezone=utc"}
        )
        Base.prepare(engine, reflect=True)
        Car = Base.classes.car

        self.Record = Base.classes.record
        self.session = Session(engine)
        self.car = self.session.query(Car).filter_by(id=car_id).first()

    def add_record(self, filename):
        datetime_formatted = datetime.strptime(filename[:19], '%Y-%m-%d_%H:%M:%S')
        self.session.add(self.Record(file_name=filename,
                                     is_deleted=False,
                                     car=self.car,
                                     start_time=datetime_formatted))
        self.session.commit()


if __name__ == '__main__':
    connection = DBConnect('postgresql+psycopg2://video:expotorgpsw@localhost/video', 1)
    filename = '2021-10-17_12:59:12_res:cam1.avi'
    connection.add_record(filename)
