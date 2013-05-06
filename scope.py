import random
import threading
import time

class Scope(object):
    def __init__(self):
        self.data = []
        self.read_thread = self.ReadThread(self)

    def get_data(self):
        data = self.data
        self.data = []
        return data

    class ReadThread(threading.Thread):
        def __init__(self, scope):
            super(Scope.ReadThread, self).__init__()
            self.scope = scope
            self.stopped = True

        def run(self):
            self.stopped = False
            while not self.stopped:
                self.scope.data.append(random.randint(-5, 5))
                time.sleep(1)
        
        def stop(self):
            self.stopped = True
