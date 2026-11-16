"""Database-only tests: python -m unittest backend.scripts.test_sprint3_database -v"""
import sqlite3
import unittest
from pathlib import Path
from backend.data_access.repositories import ShowtimeRepository, BookingRepository, parse_runtime_minutes

SCHEMA = Path(__file__).resolve().parents[1] / 'data_access' / 'schema.sql'


class Sprint3DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(':memory:')
        self.conn.row_factory = sqlite3.Row
        self.conn.execute('PRAGMA foreign_keys = ON')
        self.conn.executescript(SCHEMA.read_text(encoding='utf-8'))
        self.conn.execute("INSERT INTO movies(title,genre,status,runtime) VALUES('Demo','Drama','CURRENTLY_RUNNING','2 hr 4 min')")
        self.conn.execute("INSERT INTO theaters(name) VALUES('Demo Theater')")
        self.conn.execute("INSERT INTO showrooms(theater_id,room_number) VALUES(1,'Screen 1')")
        self.conn.executemany("INSERT INTO seats(room_id,row_label,seat_number) VALUES(1,?,?)", [('A',n) for n in range(1,9)])
        self.show_id = ShowtimeRepository.create(self.conn,1,1,'2099-01-01','14:00')

    def tearDown(self):
        self.conn.close()

    def test_show_has_correct_seats(self):
        result = ShowtimeRepository.seat_map(self.conn,self.show_id)
        self.assertEqual(8,len(result['seats']))
        self.assertTrue(all(x['status']=='AVAILABLE' for x in result['seats']))

    def test_duplicate_showtime_rejected(self):
        with self.assertRaises(sqlite3.IntegrityError):
            ShowtimeRepository.create(self.conn,1,1,'2099-01-01','14:00')

    def test_overlap_within_runtime_rejected(self):
        self.assertTrue(ShowtimeRepository.conflicts(self.conn,1,'2099-01-01','15:00',120))
        self.assertFalse(ShowtimeRepository.conflicts(self.conn,1,'2099-01-01','17:00',120))

    def test_draft_round_trip(self):
        BookingRepository.save_draft(self.conn,'draft',self.show_id,[1,2],{'ADULT':1,'CHILD':1,'SENIOR':0})
        draft = BookingRepository.get_draft(self.conn,'draft')
        self.assertEqual([1,2],draft['seats'])
        self.assertEqual(1,draft['types']['CHILD'])

    def test_runtime_parser(self):
        self.assertEqual(124,parse_runtime_minutes('2 hr 4 min'))
        self.assertEqual(180,parse_runtime_minutes('3 hr'))
        self.assertIsNone(parse_runtime_minutes('TBD'))

    def test_foreign_keys(self):
        self.assertEqual([],self.conn.execute('PRAGMA foreign_key_check').fetchall())


if __name__ == '__main__':
    unittest.main()
