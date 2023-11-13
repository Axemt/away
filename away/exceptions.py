
class FaasReturnedError(Exception):
    def __init__(self, message):            
        super().__init__(message)

class EnsureException(Exception):
    def __init__(self, message):            
        super().__init__(message)

class FaasServiceUnavailableException(Exception):
    def __init__(self, message):            
        super().__init__(message)