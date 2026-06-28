import hashlib
import os
from ..constants import SHARED_SECRET

def generate_challenge(): 
    return os.urandom(16).hex()

def get_challenge_response(challenge):
    return hashlib.sha256((challenge + SHARED_SECRET).encode()).hexdigest()

def validate_token(challenge, received):
    return get_challenge_response(challenge) == received
