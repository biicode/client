from biicode.client.dev.python.python_dynlib_adapter_generator import PythonDynLibAdapterGenerator
import os
import argparse


class PythonToolChain(object):
    '''EXPERIMENTAL Python tools commands'''
    group = 'python'

    def __init__(self, bii):
        self.bii = bii
        #Run.pre_run = ['clean', '_generate_dynlib_adapter']

    def _generate_dynlib_adapter(self):
        pydynlib_adapter_gen = PythonDynLibAdapterGenerator(self.workspace,
                                                            self.paths,
                                                            self.user_io)
        pydynlib_adapter_gen.generate_dynlib_adapter()

    def clean(self, *parameters):
        '''removes pyc files in order to do a clean run. It will be called
        automatically before each python:run'''
        parser = argparse.ArgumentParser(description=self.clean.__doc__,
                                         prog="bii %s:clean" % self.group)
        args = parser.parse_args(*parameters)

        for folder in self.paths.src, self.paths.dep:
            for root, _, files in os.walk(folder):
                for f in files:
                    if f.lower().endswith('.pyc'):
                        os.remove(os.path.join(root, f))
