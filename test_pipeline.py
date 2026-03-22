import unittest
import numpy as np
import hashlib
from database import init_db, db_register_voter, db_get_voter, db_mark_voted, db_cast_vote
import os
import sqlite3

class TestSmartVoting(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Override DB for testing (or use a test DB)
        import database
        database.DB_NAME = 'database/test_voting.db'
        if os.path.exists(database.DB_NAME):
            os.remove(database.DB_NAME)
        init_db()

    def test_1_register_voter(self):
        # Mock encoding (128-d vector)
        mock_encoding = np.random.rand(128)
        success, msg = db_register_voter('999999999999', 'TEST1234567', 'Test Voter', mock_encoding)
        self.assertTrue(success)
        
        # Duplicate test
        success2, msg2 = db_register_voter('999999999999', 'TEST1234567', 'Test Voter', mock_encoding)
        self.assertFalse(success2)

    def test_2_fetch_voter(self):
        voter = db_get_voter('999999999999', 'TEST1234567')
        self.assertIsNotNone(voter)
        self.assertEqual(voter['name'], 'Test Voter')
        self.assertFalse(voter['has_voted'])
        self.assertEqual(len(voter['face_encoding']), 128)

    def test_3_voting_logic(self):
        voter = db_get_voter('999999999999', 'TEST1234567')
        db_id = voter['id']
        
        candidate_id = 2
        secret = "test_secret"
        
        # Hash vote
        vote_string = f"{db_id}-{candidate_id}-{secret}"
        encrypted_vote = hashlib.sha256(vote_string.encode()).hexdigest()
        
        db_cast_vote(candidate_id, encrypted_vote)
        db_mark_voted(db_id)
        
        # Re-fetch
        voter_after = db_get_voter('999999999999', 'TEST1234567')
        self.assertTrue(voter_after['has_voted'])

if __name__ == '__main__':
    unittest.main()
