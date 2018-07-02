# System Libraries
import os
import collections
import traceback

# To Read Robot XML
import xmltodict
import datetime
import time

# To Send Results to Report Portal
from reportportal_client import ReportPortalServiceAsync

# Reading XML
def xml_to_dictionary(xmlfile):
    with open(xmlfile) as fd:
        doc = xmltodict.parse(fd.read())
    return doc

# Error handler for report portal
def my_error_handler(exc_info):
    """
    This callback function will be called by async service client when error occurs.
    Return True if error is not critical and you want to continue work.
    :param exc_info: result of sys.exc_info() -> (type, value, traceback)
    :return:
    """
    print("Error occurred: {}".format(exc_info[1]))
    traceback.print_exception(*exc_info)

# Get all Time stamp from xml
def get_all_timestamp(list_dic):
    output = []
    if type(list_dic) == collections.OrderedDict or type(list_dic) == dict:    
        for eachitem in list_dic:
            if type(list_dic[eachitem]) == collections.OrderedDict or type(list_dic[eachitem]) == dict:                
                if "@timestamp" in list_dic[eachitem]:
                    output.append(list_dic[eachitem]["@timestamp"][:-4])
            output.extend(get_all_timestamp(list_dic[eachitem]))
    elif type(list_dic) == list:
        for eachitem in list_dic:
            if type(eachitem) == collections.OrderedDict or type(eachitem) == dict:                                                
                if "@timestamp" in eachitem:
                    output.append(eachitem["@timestamp"][:-4])
            output.extend(get_all_timestamp(eachitem))
    return output

# Get Start and End Time stamp
def get_start_end_timestamp(list_dic):
    if type(list_dic) == collections.OrderedDict or type(list_dic) == dict:
        if "status" in list_dic:
            if "@endtime" in list_dic["status"] and "@starttime" in list_dic["status"]:
                if list_dic["status"]["@endtime"] != "N/A" and list_dic["status"]["@starttime"] != "N/A":
                    start_time = int(time.mktime(time.strptime(str(list_dic["status"]["@starttime"][:-4]), '%Y%m%d %H:%M:%S')))
                    end_time = int(time.mktime(time.strptime(str(list_dic["status"]["@endtime"][:-4]), '%Y%m%d %H:%M:%S')))
                    return start_time, end_time
    alltimestamp = get_all_timestamp(list_dic)
    alltimestamp = [int(time.mktime(time.strptime(str(strtimestamp), '%Y%m%d %H:%M:%S'))) for strtimestamp in alltimestamp]
    if alltimestamp != []:
        start_time = min(alltimestamp)
        end_time = max(alltimestamp)    
        return start_time, end_time
    else:
        return 0, 0

# Setting up Report portal connection
def connect_to_report_portal(reportport_url, project, login_token):
    service = ReportPortalServiceAsync(endpoint=reportport_url, project=project,
                                   token=login_token, error_handler=my_error_handler)
    return service

def log_results_to_portal(obj_report_portal, robot_xml_dict):
    # Get Start and End time of Launch in epoch format
    launch_start_time, launch_end_time = get_start_end_timestamp(robot_xml_dict)

    # Start launch - Main suite in robot is launch in report portal
    launch = obj_report_portal.start_launch(name=robot_xml_dict["robot"]["suite"]["@name"],
                                start_time=launch_start_time*1000,
                                description="Velo Nightly run on " + str(datetime.datetime.fromtimestamp(launch_start_time).strftime("%B %d, %Y")))
    
    update_all_tests(obj_report_portal, robot_xml_dict["robot"]["suite"])
    
    # Finish launch.
    obj_report_portal.finish_launch(end_time=launch_end_time*1000)

def get_all_logs(xml_element):

    # Ranking error code
    errcode = dict()
    errcode["ERROR"] = 1
    errcode["FAIL"] = 1
    errcode["WARN"] = 2
    errcode["TRACE"] = 3
    errcode["DEBUG"] = 4
    errcode["INFO"] = 5

    str_log = ""    
    int_level = 10
    str_level = ""
    str_time = long(7258118400000) # Epich Timestamp in millisecond of jan 1st 2200
    if type(xml_element) == collections.OrderedDict or type(xml_element) == dict:   
        for eachelement in xml_element:
            if eachelement ==  "kw":
                if type(xml_element[eachelement]) == collections.OrderedDict or type(xml_element[eachelement]) == dict:                                                       
                    if "@type" not in xml_element[eachelement]:
                        str_log = str_log + "=" * 25 + xml_element[eachelement]["@name"] + "=" * 25 + "\n"
                if type(xml_element[eachelement]) == list:
                    for eachlistitem in xml_element[eachelement]:
                        if "@type" not in eachlistitem:
                            str_log = str_log + "=" * 25 + eachlistitem["@name"] + "=" * 25 + "\n"
                            c_log, c_level, c_time = get_all_logs(eachlistitem)
                            if c_log != "":
                                str_log  = str_log + "\n\n" + c_log
                            if c_level in errcode:
                                if errcode[c_level] < int_level:
                                    int_level = errcode[c_level]
                            else:
                                print "Atten : New error level " + c_level                            
                            if str_time > c_time:
                                str_time = c_time
            elif eachelement == "msg":
                if type(xml_element[eachelement]) == collections.OrderedDict or type(xml_element[eachelement]) == dict:
                    curr_element_time = int(time.mktime(time.strptime(str(xml_element[eachelement]["@timestamp"][:-4]), '%Y%m%d %H:%M:%S')))*1000
                    if str_time > curr_element_time:
                        str_time = curr_element_time
                    str_log = str_log + str(xml_element[eachelement]["@timestamp"][:-4]) + " : " + eachmsgitem["@level"] + " : " + xml_element[eachelement]["#text"] + "\n"
                    
                    if xml_element[eachelement]["@level"] in errcode:
                        if errcode[xml_element[eachelement]["@level"]] < int_level:
                            int_level = errcode[xml_element[eachelement]["@level"]]
                    else:
                        print "Atten : New error level " + xml_element[eachelement]["@level"]                                             
                    
                elif type(xml_element[eachelement]) == list:                        
                        for eachmsgitem in xml_element[eachelement]:
                            curr_element_time = int(time.mktime(time.strptime(str(eachmsgitem["@timestamp"][:-4]), '%Y%m%d %H:%M:%S')))*1000                            
                            if str_time > curr_element_time:
                                str_time = curr_element_time
                            str_log = str_log + str(eachmsgitem["@timestamp"][:-4]) + " : " + eachmsgitem["@level"] + " : " + eachmsgitem["#text"] + "\n"
                            if eachmsgitem["@level"] in errcode:
                                if errcode[eachmsgitem["@level"]] < int_level:
                                    int_level = errcode[eachmsgitem["@level"]]
                            else:
                                print "Atten : New error level " + eachmsgitem["@level"]                            
    else:
        print "something wrong in the assumption of no list of list in robot xml structure : " + str(xml_element)
    if int_level == 10:
        str_level = "INFO"
    else:
        for key, value in errcode.items():
            if value == int_level:
                str_level = key                
                break
    
    if str_level == "":
        str_level = "INFO"
    if str_level == "FAIL":
        str_level = "ERROR"
    str_level = str_level.lower() # report portal expects log levels in lower case
    return str_log, str_level, str_time

def update_all_tests(obj_report_portal, xml_element):
    # Suite - Suite
    # Test - Test
    # KW - Step
    # KW - type - setup - before class
    # KW - type - teardown - after class
    # KW - type - testsetup - before method
    # KW - type - testteardown - after method
    # msg - log    
    
    if type(xml_element) == collections.OrderedDict or type(xml_element) == dict:
        for eachelement in xml_element:             
            itemtype = None
            if eachelement == "suite":
                itemtype = "SUITE"
            if eachelement == "test":
                itemtype = "STEP"  # ignoring test class and mark that as test (in report portal test is test class and step is test)
            if eachelement == "kw":
                itemtype = "kw"
            if "@type" in xml_element[eachelement]:                    
                if xml_element[eachelement]["@type"] == "setup":
                    itemtype = "BEFORE_CLASS"
                if xml_element[eachelement]["@type"] == "teardown":
                    itemtype = "AFTER_CLASS"
                if xml_element[eachelement]["@type"] == "testsetup":
                    itemtype = "BEFORE_METHOD"
                if xml_element[eachelement]["@type"] == "testteardown":
                    itemtype = "AFTER_METHOD"                            
            if itemtype:
                test_item_start_time, test_item_end_time = get_start_end_timestamp(xml_element[eachelement])                 
                if type(xml_element[eachelement]) == collections.OrderedDict or type(xml_element[eachelement]) == dict:
                    if itemtype != "kw":
                        obj_report_portal.start_test_item(name=xml_element[eachelement]["@name"],
                                description="",
                                tags=["nightly"],
                                start_time=test_item_start_time*1000,
                                item_type=itemtype)   
                        if itemtype == "STEP":
                            if "kw" in xml_element[eachelement]:
                                if type(xml_element[eachelement]["kw"]) == collections.OrderedDict or type(xml_element[eachelement]["kw"]) == dict: 
                                    str_log = ""
                                    str_level = ""
                                    str_time = 0
                                    str_log, str_level, str_time = get_all_logs(xml_element[eachelement]["kw"])
                                    if  str_log != "" and str_time > 0:
                                        obj_report_portal.log(
                                                long(str_time),
                                                xml_element[eachelement]["kw"]["@name"],
                                                str_level,
                                                attachment=str_log)
                                elif type(xml_element[eachelement]["kw"]) == list:
                                    for eachkwelement in xml_element[eachelement]["kw"]:
                                        str_log = ""
                                        str_level = ""
                                        str_time = 0
                                        str_log, str_level, str_time = get_all_logs(eachkwelement)
                                        if  str_log != "" and str_time > 0:
                                            obj_report_portal.log(
                                                    long(str_time),
                                                    eachkwelement["@name"],
                                                    str_level,
                                                    attachment=str_log)
                        else:                 
                            str_log = ""
                            str_level = ""
                            str_time = 0
                            str_log, str_level, str_time = get_all_logs(xml_element[eachelement])
                            if  str_log != "" and str_time > 0:
                                obj_report_portal.log(
                                        long(str_time),
                                        xml_element[eachelement]["@name"],
                                        str_level,
                                        attachment=str_log)
                    update_all_tests(obj_report_portal, xml_element[eachelement])
                    if itemtype != "kw":
                        status="PASSED"
                        if "status" in xml_element[eachelement]:
                            if "@status" in xml_element[eachelement]["status"]:
                                if xml_element[eachelement]["status"]["@status"] == "FAIL":
                                    status="FAILED"
                        obj_report_portal.finish_test_item(end_time=test_item_end_time*1000, status=status)
                elif type(xml_element[eachelement]) == list:
                    for eachlistitem in xml_element[eachelement]:                        
                        if "@type" in eachlistitem:                    
                            if eachlistitem["@type"] == "setup":
                                itemtype = "BEFORE_CLASS"
                            if eachlistitem["@type"] == "teardown":
                                itemtype = "AFTER_CLASS"
                            if eachlistitem["@type"] == "testsetup":
                                itemtype = "BEFORE_METHOD"
                            if eachlistitem["@type"] == "testteardown":
                                itemtype = "AFTER_METHOD"
                        if itemtype != "kw":
                            obj_report_portal.start_test_item(name=eachlistitem["@name"],
                                description="",
                                tags=["nightly"],
                                start_time=test_item_start_time*1000,
                                item_type=itemtype)
                            if itemtype == "STEP":
                                if "kw" in eachlistitem:
                                    if type(eachlistitem["kw"]) == collections.OrderedDict or type(eachlistitem["kw"]) == dict: 
                                        str_log = ""
                                        str_level = ""
                                        str_time = 0
                                        str_log, str_level, str_time = get_all_logs(eachlistitem["kw"])
                                        if  str_log != "" and str_time > 0:
                                            obj_report_portal.log(
                                                    long(str_time),
                                                    eachlistitem["kw"]["@name"],
                                                    str_level,
                                                    attachment=str_log)
                                    elif type(eachlistitem["kw"]) == list:
                                        for eachkwelement in eachlistitem["kw"]:
                                            str_log = ""
                                            str_level = ""
                                            str_time = 0
                                            str_log, str_level, str_time = get_all_logs(eachkwelement)
                                            if  str_log != "" and str_time > 0:
                                                obj_report_portal.log(
                                                        long(str_time),
                                                        eachkwelement["@name"],
                                                        str_level,
                                                        attachment=str_log)
                            else:
                                str_log = ""
                                str_level = ""
                                str_time = 0
                                str_log, str_level, str_time = get_all_logs(eachlistitem)
                                if  str_log != "" and str_time > 0:
                                    obj_report_portal.log(
                                            long(str_time),
                                            eachlistitem["@name"],
                                            str_level,
                                            attachment=str_log)
                    	update_all_tests(obj_report_portal, eachlistitem)
                    	if itemtype != "kw":
                            status="PASSED"
                            if "status" in eachlistitem:
                                if "@status" in eachlistitem["status"]:
                                    if eachlistitem["status"]["@status"] == "FAIL":
                                        status="FAILED"
                            obj_report_portal.finish_test_item(end_time=test_item_end_time*1000, status=status)
                elif type(xml_element[eachelement]) == list:
                    for eachlistitem in xml_element[eachelement]:                        
                        if "@type" in eachlistitem:                    
                            if eachlistitem["@type"] == "setup":
                                itemtype = "BEFORE_CLASS"
                            if eachlistitem["@type"] == "teardown":
                                itemtype = "AFTER_CLASS"
                            if eachlistitem["@type"] == "testsetup":
                                itemtype = "BEFORE_METHOD"
                            if eachlistitem["@type"] == "testteardown":
                                itemtype = "AFTER_METHOD"
                        if itemtype != "kw":
                            obj_report_portal.start_test_item(name=eachlistitem["@name"],
                                description="",
                                tags=["nightly"],
                                start_time=test_item_start_time*1000,
                                item_type=itemtype)
                            if itemtype == "STEP":
                                if "kw" in eachlistitem:
                                    if type(eachlistitem["kw"]) == collections.OrderedDict or type(eachlistitem["kw"]) == dict: 
                                        str_log = ""
                                        str_level = ""
                                        str_time = 0
                                        str_log, str_level, str_time = get_all_logs(eachlistitem["kw"])
                                        if  str_log != "" and str_time > 0:
                                            obj_report_portal.log(
                                                    long(str_time),
                                                    eachlistitem["kw"]["@name"],
                                                    str_level,
                                                    attachment=str_log)
                                    elif type(eachlistitem["kw"]) == list:
                                        for eachkwelement in eachlistitem["kw"]:
                                            str_log = ""
                                            str_level = ""
                                            str_time = 0
                                            str_log, str_level, str_time = get_all_logs(eachkwelement)
                                            if  str_log != "" and str_time > 0:
                                                obj_report_portal.log(
                                                        long(str_time),
                                                        eachkwelement["@name"],
                                                        str_level,
                                                        attachment=str_log)
                            else:
                                str_log = ""
                                str_level = ""
                                str_time = 0
                                str_log, str_level, str_time = get_all_logs(eachlistitem)
                                if  str_log != "" and str_time > 0:
                                    obj_report_portal.log(
                                            long(str_time),
                                            eachlistitem["@name"],
                                            str_level,
                                            attachment=str_log)
                        update_all_tests(obj_report_portal, eachlistitem)
                        if itemtype != "kw":
                            status="PASSED"
                            if "status" in eachlistitem:
                                if "@status" in eachlistitem["status"]:
                                    if eachlistitem["status"]["@status"] == "FAIL":
                                        status="FAILED"
                            obj_report_portal.finish_test_item(end_time=test_item_end_time*1000, status=status)
    else:
        print "something wrong in the assumption of no list of list in robot xml structure : " + str(xml_element)

def main():
    xml_doc = xml_to_dictionary("<xmlfile>")
    if xml_doc.keys()[0] == "robot":   
        reportport_url = "<report_portal_url>"
        project = "<project_name>"
        # You can get UUID from user profile page in the Report Portal.
        login_token = "<UUID>"
        # launch_name = "Test launch"
        # launch_doc = "Testing logging with attachment."
        obj_report_portal = connect_to_report_portal(reportport_url, project, login_token)
        log_results_to_portal(obj_report_portal, xml_doc)
        # Due to async nature of the service we need to call terminate() method which
        # ensures all pending requests to server are processed.
        # Failure to call terminate() may result in lost data.
        obj_report_portal.terminate()
    else:
        print "not seems like robot test"

main()