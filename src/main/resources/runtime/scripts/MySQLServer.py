import os
import time
import sys
import os.path
import re
import stat

import java.sql


from distutils import dir_util, file_util
from subprocess import call, Popen, PIPE

from java.net import InetAddress
from java.util import Properties

from com.datasynapse.fabric.common import RuntimeContextVariable
import com.mysql.jdbc.Driver

class MySQLServer:
    def __init__(self, additionalVariables):
        " initialize mysql database"
        
        self.__getHostName()
        
        additionalVariables.add(RuntimeContextVariable("MYSQL_HOST", self.__hostname, RuntimeContextVariable.ENVIRONMENT_TYPE, "", True, RuntimeContextVariable.NO_INCREMENT))
        additionalVariables.add(RuntimeContextVariable("RESTART_ENGINE_ON_DEACTIVATION", "true", RuntimeContextVariable.STRING_TYPE))
      
        self.__serverUser = getVariableValue("MYSQL_SERVER_USER")
        self.__rootPwd = getVariableValue("MYSQL_ROOT_PASSWD")
        
        self.__dbUser = getVariableValue("DATABASE_USER")
        self.__dbPwd = getVariableValue("DATABASE_PASSWORD")
        
        self.__basedir = getVariableValue("MYSQL_BASE")
        
        self.__bindir = os.path.join(self.__basedir, "bin")
        changePermissions(self.__bindir)
        
        self.__mysqld = cmd = os.path.join(self.__bindir, "mysqld")
        self.__mysql = cmd = os.path.join(self.__bindir, "mysql")
        self.__mysqladmin = cmd = os.path.join(self.__bindir, "mysqladmin")
        
        self.__defaultsFile = getVariableValue("MYSQL_CONFIG_FILE")
        self.__initDbSql = getVariableValue("MYSQL_INIT_SQL")
        
        self.__mysqlHome = getVariableValue("MYSQL_HOME")
        if not os.path.isdir(self.__mysqlHome):
            mkdir_p(self.__mysqlHome)
           
        self.__tmp = getVariableValue("TMPDIR") 
        mkdir_p(self.__tmp)
        
        self.__pwdfile = os.path.join(self.__tmp, ".#p")
        
        self.__datadir = getVariableValue("MYSQL_DATA") 
        if not os.path.isdir(self.__datadir) or not os.listdir(self.__datadir):
            dbDataClone = getVariableValue("MYSQL_DATA_CLONE")
            if dbDataClone and os.path.isdir(dbDataClone):
                shutil.copytree(dbDataClone, self.__datadir)
                self.__secured = True
            else:
                mkdir_p(self.__datadir)
                self.__secured = False
        else:
            self.__secured = True
            
        self.__tcpPort = getVariableValue("TCP_PORT")
        additionalVariables.add(RuntimeContextVariable("MYSQL_PORT", self.__tcpPort, RuntimeContextVariable.STRING_TYPE, "", True, RuntimeContextVariable.NO_INCREMENT))
        self.__dbName = getVariableValue("DATABASE_NAME")
        additionalVariables.add(RuntimeContextVariable("MYSQL_DB", self.__dbName, RuntimeContextVariable.STRING_TYPE, "", True, RuntimeContextVariable.NO_INCREMENT))
        
        self.__rootJdbcUrl = "jdbc:mysql://localhost:"+ self.__tcpPort + "/mysql"
        self.__jdbcUrl = "jdbc:mysql://" + self.__hostname +":"+ self.__tcpPort + "/" + self.__dbName
        runtimeContext.addVariable(RuntimeContextVariable("JDBC_URL", self.__jdbcUrl, RuntimeContextVariable.STRING_TYPE, "", True, RuntimeContextVariable.NO_INCREMENT))
    
        self.__mysqlUnixPort = getVariableValue("MYSQL_UNIX_PORT")
        self.__databases = []
        
    def __getHostName(self):
        "get hostname"
        self.__hostname = getVariableValue("ENGINE_USERNAME");
        try:
            hostname = InetAddress.getLocalHost().getCanonicalHostName()
            if hostname != "localhost" and not re.search("[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+", hostname):
                self.__hostname = hostname
        except:
            type, value, traceback = sys.exc_info()
            logger.severe("get hostname error:" + `value`)
            
    def __initDb(self):
        "init db"
        
        cmdList = [self.__mysqld, "--initialize-insecure",  "--user=" + self.__serverUser, "--explicit-defaults-for-timestamp", "--basedir="+self.__basedir, "--datadir="+self.__datadir, "--init-file="+self.__initDbSql]
        logger.info("Executing:"+ list2str(cmdList))
        retcode = call(cmdList)
        logger.info("Exit code:" + `retcode`)
        
        path = os.path.join(self.__basedir, "my.cnf")
        if os.path.isfile(path):
            os.remove(path)
       
        self.__secured = True
      
    
    def __createConnection(self):
        "create database"
        self.__connection = None
        try:
            logger.info("RegisterJDBC driver: com.mysql.jdbc.Driver")
            driver = com.mysql.jdbc.Driver.newInstance()
            if driver and driver.acceptsURL(self.__rootJdbcUrl):
                props = Properties()
                props.setProperty("user", "root")
                props.setProperty("password", self.__rootPwd)
           
                logger.info("Create JDBC connection:" + self.__rootJdbcUrl)
                self.__connection = driver.connect(self.__rootJdbcUrl, props)
            if self.__connection:
                logger.info("Create db select prepared statement")
                self.__dbstmt = self.__connection.prepareStatement("show databases;")
                
                rs = self.__dbstmt.executeQuery()
                self.__databases = []
                while (rs.next()):
                    db = rs.getString(1)
                    self.__databases.append(db)
        except:
            self.__connection = None
            type, value, traceback = sys.exc_info()
            logger.severe("create connection error:" + `value`)
            
    def __createDatabase(self):
        " create database"
        try:
            stmt = self.__connection.createStatement()
            logger.info("create database:" + self.__dbName)
            create = "CREATE DATABASE " + self.__dbName + " ;"
            stmt.executeUpdate(create)
            stmt.close()
        except:
            type, value, traceback = sys.exc_info()
            logger.severe("create database error:" + `value`)
    
    def __createUserIfNotExists(self):
        " create user"
        try:
            stmt = self.__connection.createStatement()
        
            create = "CREATE USER IF NOT EXISTS " + self.__dbUser + "@'%' IDENTIFIED BY '" + self.__dbPwd + "';"
            logger.info("create user:" + create)
            stmt.executeUpdate(create)
            stmt.close()
        except:
            type, value, traceback = sys.exc_info()
            logger.warning("create user error:" + `value` +"; error may be ignored if user already exists")
            
    def startServer(self):
        "start Mysqld"
        
        if not self.__secured:
            self.__initDb()
            
        file_util.copy_file(self.__defaultsFile, self.__mysqlHome)
        
        copyContainerEnvironment()
      
        cmdList = [self.__mysqld, "--defaults-file=" + self.__defaultsFile, "--basedir="+self.__basedir, "--datadir="+self.__datadir]
        logger.info("Executing:" + list2str(cmdList))  
        self.__mysqldProcess = Popen(cmdList)
        
    def shutdownServer(self):
        "shutdown Mysqld"
        copyContainerEnvironment()
        
        file = None
        try:
            file = open(self.__pwdfile, "w")
            file.write(self.__rootPwd +"\n")
            file.close()
            file = open(self.__pwdfile, "r")
            cmdList = [self.__mysqladmin, "--defaults-file=" + self.__defaultsFile, "--user=root", "--host=localhost", "-p", "shutdown"]
            logger.info("Executing:" + list2str(cmdList))  
            process = Popen(cmdList, stdin=file)
            retcode = process.wait()
            logger.info("Shutdown mysqld exit code:" + `retcode`)
        except:
            type, value, traceback = sys.exc_info()
            logger.severe("shutdown error:" + `value`)
        finally:
            if file:
                file.close()
                
            if self.__dbstmt:
                try:
                    self.__dbstmt.close()
                except:
                    type, value, traceback = sys.exc_info()
                    logger.severe("shutdown error:" + `value`)
                finally:
                    self.__dbstmt = None
                    
            if self.__connection:
                try:
                    self.__connection.close()
                except:
                    type, value, traceback = sys.exc_info()
                    logger.severe("shutdown error:" + `value`)
                finally:
                    self.__connection = None
        
    def doInstall(self, info):
        "install activation info"
         
        if self.__dbName not in self.__databases:
            self.__createDatabase()
            
        self.__createUserIfNotExists()
        self.__grantPrivileges(self.__dbName)
        self.__grantPrivileges("mysql")
        
        propertyName="MySQL Host"
        propertyValue = self.__hostname
        logger.info("Set activation info:" + propertyName + " = " + propertyValue)
        info.setProperty(propertyName, propertyValue)
        
        propertyName="MySQL Port"
        propertyValue = self.__tcpPort
        logger.info("Set activation info:" + propertyName + " = " + propertyValue)
        info.setProperty(propertyName, propertyValue)
        
        propertyName="MySQL Database"
        propertyValue = self.__dbName
        logger.info("Set activation info:" + propertyName + " = " + propertyValue)
        info.setProperty(propertyName, propertyValue)
        
        propertyName="MySQL Jdbc Url"
        propertyValue = self.__jdbcUrl
        logger.info("Set activation info:" + propertyName + " = " + propertyValue)
        info.setProperty(propertyName, propertyValue)
    
    def __grantPrivileges(self, db):
        " grant privileges"
        try:
            stmt = self.__connection.createStatement()
            update = "GRANT ALL PRIVILEGES ON " + db + ".* TO '" + self.__dbUser + "'@'%' ;"
            logger.info("Execute update:" + update)
            stmt.executeUpdate(update)
            stmt.close()
        except:
            type, value, traceback = sys.exc_info()
            logger.severe("grantPrivileges error:" + `value`)
            
    def isServerRunning(self):
        " is server running"
        running = False
        
        try:
            rs = self.__dbstmt.executeQuery()
            if (rs.next()):
                running = True
        except:
            type, value, traceback = sys.exc_info()
            logger.severe("isServerRunning error:" + `value`)
            
        return running
    
    def hasServerStarted(self):
        "has server started"
        
        started = False
        
        if self.__secured:
            self.__createConnection()
            started =  self.__connection != None
        
        logger.info("server has started:" + `started`)
        
        return started
    

def copyContainerEnvironment():
    count = runtimeContext.variableCount
    for i in range(0, count, 1):
        rtv = runtimeContext.getVariable(i)
        if rtv.type == "Environment":
            os.environ[rtv.name] = rtv.value
    
    os.unsetenv("LD_LIBRARY_PATH")
    os.unsetenv("LD_PRELOAD")

def list2str(list):
    content = str(list).strip('[]')
    content =content.replace(",", " ")
    content =content.replace("u'", "")
    content =content.replace("'", "")
    return content

def getVariableValue(name, value=None):
    "get runtime variable value"
    var = runtimeContext.getVariable(name)
    if var != None:
        value = var.value
    
    return value

def mkdir_p(path, mode=0700):
    if not os.path.isdir(path):
        logger.info("Creating directory:" + path)
        os.makedirs(path, mode)
        
def changePermissions(dir):
    logger.info("chmod:" + dir)
    os.chmod(dir, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
      
    for dirpath, dirnames, filenames in os.walk(dir):
        for dirname in dirnames:
            dpath = os.path.join(dirpath, dirname)
            os.chmod(dpath, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
           
        for filename in filenames:
               filePath = os.path.join(dirpath, filename)
               os.chmod(filePath, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
                

def doStart():
    "do start"
    logger.info("MySQLServerContainer: doStart:Enter")
    try:
        mysqlServer = getVariableValue("MYSQL_SERVER_OBJECT")
        
        if mysqlServer:
            started = mysqlServer.startServer()
            
    except:
        type, value, traceback = sys.exc_info()
        logger.severe("Unexpected error in MySQLServerContainer:doStart:" + `value`)
        
    logger.info("MySQLServerContainer: doStart:Exit")
    
def doShutdown():
    "do shutdown"
    logger.info("MySQLServerContainer: doShutdown:Enter")
    try:
        mysqlServer = getVariableValue("MYSQL_SERVER_OBJECT")
        
        if mysqlServer:
            mysqlServer.shutdownServer()
            
    except:
        type, value, traceback = sys.exc_info()
        logger.severe("Unexpected error in MySQLServerContainer:doShutdown:" + `value`)
        
    logger.info("MySQLServerContainer: doShutdown:Exit")
    
def doInit(additionalVariables):
    "do init"
    logger.info("MySQLServerContainer: doInit:Enter")
    mysqlServer = MySQLServer(additionalVariables)
    mysqlServerRcv = RuntimeContextVariable("MYSQL_SERVER_OBJECT", mysqlServer, RuntimeContextVariable.OBJECT_TYPE)
    runtimeContext.addVariable(mysqlServerRcv)
    logger.info("MySQLServerContainer: doInit:Exit")
    
def hasContainerStarted():
    started = False
    try:
        mysqlServer = getVariableValue("MYSQL_SERVER_OBJECT")
        
        if mysqlServer:
            started = mysqlServer.hasServerStarted()
            
    except:
        type, value, traceback = sys.exc_info()
        logger.severe("Unexpected error in MySQLServerContainer:hasContainerStarted:" + `value`)
    
    return started
    
def isContainerRunning():
    running = False
    try:
        mysqlServer = getVariableValue("MYSQL_SERVER_OBJECT")
        if mysqlServer:
            running = mysqlServer.isServerRunning()
    except:
        type, value, traceback = sys.exc_info()
        logger.severe("Unexpected error in MySQLServerContainer:isContainerRunning:" + `value`)
    
    return running

def doInstall(info):
    " do install of activation info"

    logger.info("MySQLServerContainer: doInstall:Enter")
    try:
        mysqlServer = getVariableValue("MYSQL_SERVER_OBJECT")
        if mysqlServer:
            mysqlServer.doInstall(info)
    except:
        type, value, traceback = sys.exc_info()
        logger.severe("Unexpected error in MySQLServerContainer:doInstall:" + `value`)
        
    logger.info("MySQLServerContainer: doInstall:Exit")
    

def getContainerStartConditionPollPeriod():
    return int(getVariableValue("START_POLL_PERIOD", "10000"))
    
def getContainerRunningConditionPollPeriod():
    return int(getVariableValue("RUNNING_POLL_PERIOD", "30000"))