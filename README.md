### MySql Community Edition Enabler User Guide

### Introduction
--------------------------------------
`MySql Community Edition Enabler` is used with `TIBCO Silver Fabric` to manage MySql Community Edition database. 

### Building the Enabler and Distribution
---------------------------------------------------
This enabler project builds a `Silver Fabric Enabler Grid Library`. It also optionally builds a `Silver Fabric Distribution Grid Library` for MySql Community Edition database. 
The Silver Fabric Grid Libraries can be built by executing Maven `install`. After a successful build, the Enabler and Distribution Grid Library files can be found under project `target` folder. 

To build both the Enabler and Distribution Grid Libraries:

* Download MySql Community Edition database 64-bit compressed tar file for Generic Linux from `https://dev.mysql.com/downloads/mysql/`. For example,  download `mysql-5.7.10-linux-glibc2.5-x86_64.tar.gz` to /tmp.
* Run Maven `install` target with Java system property `distribution.location` pointing to the location of down loaded MySql compressed tar file. For example, `-Ddistribution.location=/tmp/mysql-5.7.10-linux-glibc2.5-x86_64.tar.gz`

If you want to build the Enabler Grid LIbrary without building Distribution Grid Library:

* Run Maven `install` target without defining `distribution.location` Java system property

### Installing the Enabler and Distribution
----------------------------------------------------
Installation of the MySql Community Edition Enabler and Distribution is done by copying the MySql Community Edition Enabler and Distribution Grid Libraries from the `target` project folder to the `SF_HOME/webapps/livecluster/deploy/resources/gridlib` folder on the Silver Fabric Broker. 

### Enabler Features
-------------------------------------------
This Enabler supports following Silver Fabric Features:

* Application Logging Support

### Enabler Statistics
-------------------------------------
This enabler supports no statistics.

### Runtime Context Variables
---------------------------------------
Silver Fabric Components using this enabler can configure following Enabler Runtime Context variables. 

### Runtime Context Variable List:
------------------------------------------

|Variable Name|Default Value|Type|Description|Export|Auto Increment|
|---|---|---|---|---|---|
|`MYSQL_CONFIG_FILE`|${CONTAINER_WORK_DIR}/conf/my.cnf| String| MySQL config file. A default config file is included in the enabler.|false|None|
|`MYSQL_INIT_SQL`|${CONTAINER_WORK_DIR}/sql/init-db.sql|String|MySQl init  SQL script. A default script is included to secure the database.|false|None|
|`TCP_PORT`|3306|String|Database TCP listen port|false|Numeric|
|`DATABASE_NAME`|mydb|String|Database name. This database is created by enabler.|false|None|
|`DATABASE_USER`|mydbuser|String|Database user.|false|None|
|`DATABASE_PASSWORD`|MySql09!|String|Database password for DATABASE_USER.|false|None|
|`MYSQL_DATA`|${MYSQL_HOME}/data|String|MySql database data directory. Default data directory is ephemeral.|false|None|
|`MYSQL_DATA_CLONE`||String|MySQL data clone. This data directory is cloned by enabler to initialize MYSQL_DATA if it is empty.|false|None|
|`MYSQL_ROOT_PASSWD`|MySql09!|String|MySql root password|false|None|

### Component Examples
------------------------
Below are screenshot images from example Silver Fabric Component configurations using this Enabler. 
* [MySql] (images/mysql.png)