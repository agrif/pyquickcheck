from . import *

if __name__ == '__main__':
    import code
    import pkg_resources
    version = pkg_resources.require("pyquickcheck")[0].version
    code.interact(banner="pyquickcheck {}".format(version), local=locals())
