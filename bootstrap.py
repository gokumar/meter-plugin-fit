#!/usr/bin/env python
import os
import sys
import subprocess
import platform
import site
from subprocess import PIPE, Popen
if sys.version_info >= (3, 0, 0):
    import urllib.request
else:
    import urllib

class Bootstrap:

  def __init__(self,
               python="python",
               requirements="requirements.txt",
               pipGetUrl="https://bootstrap.pypa.io/get-pip.py",
               pipFileName="get-pip.py",
               isPipFound="succeeded",
               install="installPIP",
               pipCheckCmd='python -c "import pip" 2>&- && echo "succeeded" || echo "failed"',
               isPipFoundInUserLocalDir="userLocalDir"):
      
    self.python = python
    self.requirements = requirements
    self.pipGetUrl = pipGetUrl
    self.pipFileName = pipFileName
    self.isPipFound = isPipFound
    self.install = install
    self.pipCheckCmd = pipCheckCmd
    self.isPipFound = isPipFound
    self.isPipFoundInUserLocalDir = isPipFoundInUserLocalDir

  def shellcmd(self, cmd, echo=False):
    """ Run 'cmd' in the shell and return its standard out.
    """
    if not echo: print('[cmd] {0}'.format(cmd))
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    out = p.communicate()[0]
    if not echo: print(out)
    return out


  def setup(self):
    """Bootraps a python environment
    """
    if os.path.isfile(self.requirements):
      self.installLibs()
      
    
  def download(self):
    """download pip file
    """
    urllib.urlretrieve (self.pipGetUrl, self.pipFileName)

  def deleteFile(self):
    """Delete downloaded pip file
    """
    os.remove(self.pipFileName)
  

  def getPythonVersion(self):
    """Get python version
    """
    pythonVersionArray = sys.version.split(' ')[0].split(".")
    return (pythonVersionArray[0] + pythonVersionArray [1])

  def isFound(self,platformName):
    """ checking is pip is installed or not
    """
    if("Windows" in platformName):
        isFound = self.shellcmd("pip --version")
        if isFound == ' ':
          return self.install
        else:
          return self.isPipFound
    else:
        isFound = self.shellcmd(self.pipCheckCmd)
        isPipExeFileFound = self.isPipExistsInUserLocal()
        if isPipExeFileFound == True:
            return self.isPipFoundInUserLocalDir
        elif isFound.strip() == 'succeeded':
            return self.isPipFound
        else:
            return self.install
           
  
  def isPipExistsInUserLocal(self):
    """ checking  is Pip Exists In User Local
    """
    retVale = False
    try:
        retVale = os.path.exists(self.getUserLevelBasePath())
    except:
        pass

    return retVale
 
  def getUserLevelSitePackagePath(self):
    """ Getting user level site package
    """
    userLevelSitePackagePyhtonPath = "PYTHONPATH=" + site.getusersitepackages() + "/"
    return userLevelSitePackagePyhtonPath

  def getUserLevelBasePath(self):
    """ getting user level base path
    """
    userLevelBasePath = site.getuserbase() + "/bin/pip"
    return userLevelBasePath

  def installLibs(self):
    """ Install dependencies 
    """
    platformName = platform.platform(aliased=True)
    retVal = self.isFound(platformName)
    commonPipCmd = 'pip install -r {0} -t ./.pip'.format(self.requirements)
    dynamicPythonPath = self.getUserLevelSitePackagePath()
    userLevelBasePath = self.getUserLevelBasePath()
    
    if("Windows" in platformName):
        if retVal == self.install:
            self.download()
            self.shellcmd(self.python + " " + self.pipFileName)
            self.shellcmd(commonPipCmd)
            self.deleteFile()
        else:
            self.shellcmd(commonPipCmd)
    else:
        if retVal == self.isPipFoundInUserLocalDir:
            self.shellcmd(dynamicPythonPath + " " +userLevelBasePath  +' install -r {0} -t ./.pip'.format(self.requirements))
        elif retVal == self.isPipFound:
            self.shellcmd(commonPipCmd)
        else:         
            self.download()
            self.shellcmd(self.python + " " + self.pipFileName + " --user")
            self.shellcmd(dynamicPythonPath + " " + userLevelBasePath + ' install -r {0} -t ./.pip'.format(self.requirements))
            self.deleteFile()
    return

    
if __name__ == "__main__":
  bootstrap = Bootstrap()
  bootstrap.setup()
