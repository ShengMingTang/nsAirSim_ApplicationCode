from appBase import *
'''
Custom App code
'''        
class UavApp(UavAppBase):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # any self.attribute that you need
        
    def customfn(self, *args, **kwargs):
        # as your new target function
        pass

    # def run(self, **kwargs):
    #     self.beforeRun()
    #     self.streamingTest()
    #     self.afterRun()
    #     print(f'{self.name} joined')
        
class GcsApp(GcsAppBase):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # any self.attribute that you need
        
    def customfn(self, *args, **kwargs):
        # as your new target function
        pass

    # def run(self, *args, **kwargs):
    #     self.beforeRun()
    #     self.streamingTest()
    #     self.afterRun()
    #     print(f'{self.name} joined')