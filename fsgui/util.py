import uuid

class UIDManager:
    """
    Unique identifier manager. Assigns new UIDs and stores previously-assigned UIDs.
    """

    def __init__(self):
        self.uids = set()
    
    def assign(self):
        uid = None

        while uid is None or uid in self.uids:
            uid = str(uuid.uuid1())
        self.reserve(uid)
        return uid

    def reserve(self, uid):
        self.uids.add(uid)
    
    def delete(self, uid):
        self.uids.remove(uid)