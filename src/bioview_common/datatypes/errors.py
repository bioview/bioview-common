class AuthenticationError(Exception):
    """Custom exception for authentication failures"""
    pass

class ValidationError(Exception):
    """Custom exception for message validation failures"""
    pass

class DeviceError(Exception):
    """Custom exception for device-related errors"""
    pass