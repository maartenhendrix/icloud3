"""
Platform that supports scanning iCloud.
For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/device_tracker.icloud/


Special Note: I want to thank Walt Howd, (iCloud2 fame) who inspired me to
    tackle this project. I also want to give a shout out to Kovács Bálint,
    Budapest, Hungary who wrote the Python WazeRouteCalculator and some
    awesome HA guys (Petro31, scop, tsvi, troykellt, balloob, Myrddyn1,
    mountainsandcode,  diraimondo, fabaff, squirtbrnr, and mhhbob) who
    gave me the idea of using Waze in iCloud3.
                ...Gary Cobb aka GeeksterGary, Vero Beach, Florida, USA

Thanks to all
"""

#pylint: disable=bad-whitespace, bad-indentation
#pylint: disable=bad-continuation, import-error, invalid-name, bare-except
#pylint: disable=too-many-arguments, too-many-statements, too-many-branches
#pylint: disable=too-many-locals, too-many-return-statements
#pylint: disable=unused-argument, unused-variable
#pylint: disable=too-many-instance-attributes, too-many-lines

VERSION = '2.2.0rc2'
'''


'''
#Symbols = •▶¦▶ ●►◄▬▲▼◀▶ oPhone=►▶►

import logging
import os
import sys
import time
import datetime
import json
import voluptuous as vol

from   homeassistant.const                import CONF_USERNAME, CONF_PASSWORD
from   homeassistant.helpers.event        import track_utc_time_change
import homeassistant.helpers.config_validation as cv

from   homeassistant.util                 import slugify
import homeassistant.util.dt              as dt_util
from   homeassistant.util.location        import distance

from   homeassistant.components.device_tracker import (
          PLATFORM_SCHEMA, DOMAIN, ATTR_ATTRIBUTES)

_LOGGER = logging.getLogger(__name__)

#Changes in device_tracker entities are not supported in HA v0.94 and
#legacy code is being used for the DeviceScanner. Try to import from the
#.legacy directory and retry from the normal directory if the .legacy
#directory does not exist.
try:
    from homeassistant.components.device_tracker.legacy import DeviceScanner
    HA_DEVICE_TRACKER_LEGACY_MODE = True
except ImportError:
    from homeassistant.components.device_tracker import DeviceScanner
    HA_DEVICE_TRACKER_LEGACY_MODE = False

#Vailidate that Waze is available and can be used
try:
    import WazeRouteCalculator
    WAZE_IMPORT_SUCCESSFUL = 'YES'
except ImportError:
    WAZE_IMPORT_SUCCESSFUL = 'NO'
    pass

try:
    from .pyicloud_ic3 import PyiCloudService
    from .pyicloud_ic3 import (
            PyiCloudFailedLoginException,
            PyiCloudNoDevicesException,
            PyiCloudServiceNotActivatedException,
            PyiCloudAPIResponseException,
            )
    PYICLOUD_IC3_IMPORT_SUCCESSFUL = True
except ImportError:
    PYICLOUD_IC3_IMPORT_SUCCESSFUL = False
    pass

DEBUG_TRACE_CONTROL_FLAG = False

HA_ENTITY_REGISTRY_FILE_NAME='/config/.storage/core.entity_registry'
ENTITY_REGISTRY_FILE_KEY    = 'core.entity_registry'
STORAGE_KEY_ICLOUD          = 'icloud'
STORAGE_KEY_ENTITY_REGISTRY = 'core.entity_registry'
STORAGE_VERSION             = 1
STORAGE_DIR                 = ".storage"

CONF_ACCOUNT_NAME           = 'account_name'
CONF_GROUP                  = 'group'
CONF_DEVICENAME             = 'device_name'
CONF_NAME                   = 'name'
CONF_TRACKING_METHOD        = 'tracking_method'
CONF_MAX_IOSAPP_LOCATE_CNT  = 'max_iosapp_locate_cnt'
CONF_TRACK_DEVICES          = 'track_devices'
CONF_TRACK_DEVICE           = 'track_device'
CONF_UNIT_OF_MEASUREMENT    = 'unit_of_measurement'
CONF_INTERVAL               = 'interval'
CONF_BASE_ZONE              = 'base_zone'
CONF_INZONE_INTERVAL        = 'inzone_interval'
CONF_CENTER_IN_ZONE         = 'center_in_zone'
CONF_STATIONARY_STILL_TIME  = 'stationary_still_time'
CONF_STATIONARY_INZONE_INTERVAL = 'stationary_inzone_interval'
CONF_MAX_INTERVAL           = 'max_interval'
CONF_TRAVEL_TIME_FACTOR     = 'travel_time_factor'
CONF_GPS_ACCURACY_THRESHOLD = 'gps_accuracy_threshold'
CONF_OLD_LOCATION_THRESHOLD = 'old_location_threshold'
CONF_IGNORE_GPS_ACC_INZONE  = 'ignore_gps_accuracy_inzone'
CONF_HIDE_GPS_COORDINATES   = 'hide_gps_coordinates'
CONF_WAZE_REGION            = 'waze_region'
CONF_WAZE_MAX_DISTANCE      = 'waze_max_distance'
CONF_WAZE_MIN_DISTANCE      = 'waze_min_distance'
CONF_WAZE_REALTIME          = 'waze_realtime'
CONF_DISTANCE_METHOD        = 'distance_method'
CONF_COMMAND                = 'command'
CONF_CREATE_SENSORS         = 'create_sensors'
CONF_EXCLUDE_SENSORS        = 'exclude_sensors'
CONF_ENTITY_REGISTRY_FILE   = 'entity_registry_file_name'
CONF_LOG_LEVEL              = 'log_level'
CONF_CONFIG_IC3_FILE_NAME   = 'config_ic3_file_name'

# entity attributes (iCloud FmF & FamShr)
ATTR_ICLOUD_TIMESTAMP       = 'timeStamp'
ATTR_ICLOUD_HORIZONTAL_ACCURACY = 'horizontalAccuracy'
ATTR_ICLOUD_VERTICAL_ACCURACY   = 'verticalAccuracy'
ATTR_ICLOUD_BATTERY_STATUS      = 'batteryStatus'
ATTR_ICLOUD_BATTERY_LEVEL       = 'batteryLevel'
ATTR_ICLOUD_DEVICE_CLASS        = 'deviceClass'
ATTR_ICLOUD_DEVICE_STATUS       = 'deviceStatus'
ATTR_ICLOUD_LOW_POWER_MODE      = 'lowPowerMode'

# device data attributes
ATTR_LOCATION           = 'location'
ATTR_ATTRIBUTES         = 'attributes'
ATTR_RADIUS             = 'radius'
ATTR_FRIENDLY_NAME      = 'friendly_name'
ATTR_NAME               = 'name'
ATTR_ISOLD              = 'isOld'
ATTR_DEVICE_CLASS       = 'device_class'

# entity attributes
ATTR_ZONE               = 'zone'
ATTR_ZONE_TIMESTAMP     = 'zone_timestamp'
ATTR_LAST_ZONE          = 'last_zone'
ATTR_GROUP              = 'group'
ATTR_TIMESTAMP          = 'timestamp'
ATTR_TIMESTAMP_TIME     = 'timestamp_time'
ATTR_AGE                = 'age'
ATTR_TRIGGER            = 'trigger'
ATTR_BATTERY            = 'battery'
ATTR_BATTERY_LEVEL      = 'battery_level'
ATTR_BATTERY_STATUS     = 'battery_status'
ATTR_INTERVAL           = 'interval'
ATTR_ZONE_DISTANCE      = 'zone_distance'
ATTR_CALC_DISTANCE      = 'calc_distance'
ATTR_WAZE_DISTANCE      = 'waze_distance'
ATTR_WAZE_TIME          = 'travel_time'
ATTR_DIR_OF_TRAVEL      = 'dir_of_travel'
ATTR_TRAVEL_DISTANCE    = 'travel_distance'
ATTR_DEVICE_STATUS      = 'device_status'
ATTR_LOW_POWER_MODE     = 'low_power_mode'
ATTR_TRACKING           = 'tracking'
ATTR_DEVICENAME_IOSAPP  = 'iosapp_device'
ATTR_AUTHENTICATED      = 'authenticated'
ATTR_LAST_UPDATE_TIME   = 'last_update'
ATTR_NEXT_UPDATE_TIME   = 'next_update'
ATTR_LAST_LOCATED       = 'last_located'
ATTR_INFO               = 'info'
ATTR_GPS_ACCURACY       = 'gps_accuracy'
ATTR_GPS                = 'gps'
ATTR_LATITUDE           = 'latitude'
ATTR_LONGITUDE          = 'longitude'
ATTR_POLL_COUNT         = 'poll_count'
ATTR_ICLOUD3_VERSION    = 'icloud3_version'
ATTR_VERT_ACCURACY  = 'vertical_accuracy'
ATTR_ALTITUDE           = 'altitude'
ATTR_BADGE              = 'badge'
ATTR_EVENT_LOG          = 'event_log'
ATTR_PICTURE            = 'entity_picture'


TIMESTAMP_ZERO          = '0000-00-00 00:00:00'
HHMMSS_ZERO             = '00:00:00'
HIGH_INTEGER            = 9999999999
TIME_24H                = True
UTC_TIME                = True
LOCAL_TIME              = False
NUMERIC                 = True
NEW_LINE                = '\n'

SENSOR_EVENT_LOG_ENTITY = 'sensor.icloud3_event_log'

DEVICE_ATTRS_BASE       = {ATTR_LATITUDE: 0,
                           ATTR_LONGITUDE: 0,
                           ATTR_BATTERY: 0,
                           ATTR_BATTERY_LEVEL: 0,
                           ATTR_BATTERY_STATUS: '',
                           ATTR_GPS_ACCURACY: 0,
                           ATTR_VERT_ACCURACY: 0,
                           ATTR_TIMESTAMP: TIMESTAMP_ZERO,
                           ATTR_ICLOUD_TIMESTAMP: HHMMSS_ZERO,
                           ATTR_TRIGGER: '',
                           ATTR_DEVICE_STATUS: '',
                           ATTR_LOW_POWER_MODE: '',
                           }

INITIAL_LOCATION_DATA   = {'name': '',
                           'device_class': 'iPhone',
                           'battery_level': 0,
                           'battery_status': 'Unknown',
                           'device_status': '',
                           'low_power_mode': False,
                           'timestamp': 0,
                           'timestamp_time': HHMMSS_ZERO,
                           'age': HIGH_INTEGER,
                           'latitude': 0.0,
                           'longitude': 0.0,
                           'altitude': 0.0,
                           'isOld': False,
                           'gps_accuracy': 0.0,
                           'vertical_accuracy': 0.0}

TRACE_ATTRS_BASE        = {ATTR_NAME: '',
                           ATTR_ZONE: '',
                           ATTR_LAST_ZONE: '',
                           ATTR_ZONE_TIMESTAMP: '',
                           ATTR_LATITUDE: 0,
                           ATTR_LONGITUDE: 0,
                           ATTR_TRIGGER: '',
                           ATTR_TIMESTAMP: TIMESTAMP_ZERO,
                           ATTR_ZONE_DISTANCE: 0,
                           ATTR_INTERVAL: 0,
                           ATTR_DIR_OF_TRAVEL: '',
                           ATTR_TRAVEL_DISTANCE: 0,
                           ATTR_WAZE_DISTANCE: '',
                           ATTR_CALC_DISTANCE: 0,
                           ATTR_LAST_LOCATED: '',
                           ATTR_LAST_UPDATE_TIME: '',
                           ATTR_NEXT_UPDATE_TIME: '',
                           ATTR_POLL_COUNT: '',
                           ATTR_INFO: '',
                           ATTR_BATTERY: 0,
                           ATTR_BATTERY_LEVEL: 0,
                           ATTR_GPS: 0,
                           ATTR_GPS_ACCURACY: 0,
                           ATTR_VERT_ACCURACY: 0,
                           }

TRACE_ICLOUD_ATTRS_BASE = {CONF_NAME: '', 'deviceStatus': '',
                           ATTR_ISOLD: False,
                           ATTR_LATITUDE: 0,
                           ATTR_LONGITUDE: 0,
                           ATTR_ICLOUD_TIMESTAMP: 0,
                           ATTR_ICLOUD_HORIZONTAL_ACCURACY: 0,
                           ATTR_ICLOUD_VERTICAL_ACCURACY: 0,
                          'positionType': 'Wifi',
                          }

SENSOR_DEVICE_ATTRS     = ['zone',
                           'zone_name1',
                           'zone_name2',
                           'zone_name3',
                           'last_zone',
                           'last_zone_name1',
                           'last_zone_name2',
                           'last_zone_name3',
                           'zone_timestamp',
                           'base_zone',
                           'zone_distance',
                           'calc_distance',
                           'waze_distance',
                           'travel_time',
                           'dir_of_travel',
                           'interval',
                           'info',
                           'last_located',
                           'last_update',
                           'next_update',
                           'poll_count',
                           'travel_distance',
                           'trigger',
                           'battery',
                           'battery_status',
                           'gps_accuracy',
                           'vertical accuracy',
                           'badge',
                           'name',
                           ]

SENSOR_ATTR_FORMAT      = {'zone_distance': 'dist',
                           'calc_distance': 'dist',
                           'waze_distance': 'diststr',
                           'travel_distance': 'dist',
                           'battery': '%',
                           'dir_of_travel': 'title',
                           'altitude': 'm-ft',
                           'badge': 'badge',
                           }

#---- iPhone Device Tracker Attribute Templates ----- Gary -----------
SENSOR_ATTR_FNAME       = {'zone': 'Zone',
                           'zone_name1': 'Zone',
                           'zone_name2': 'Zone',
                           'zone_name3': 'Zone',
                           'last_zone': 'Last Zone',
                           'last_zone_name1': 'Last Zone',
                           'last_zone_name2': 'Last Zone',
                           'last_zone_name3': 'Last Zone',
                           'zone_timestamp': 'Zone Timestamp',
                           'base_zone': 'Base Zone',
                           'zone_distance': 'Zone Distance',
                           'calc_distance': 'Calc Dist',
                           'waze_distance': 'Waze Dist',
                           'travel_time': 'Travel Time',
                           'dir_of_travel': 'Direction',
                           'interval': 'Interval',
                           'info': 'Info',
                           'last_located': 'Last Located',
                           'last_update': 'Last Update',
                           'next_update': 'Next Update',
                           'poll_count': 'Poll Count',
                           'travel_distance': 'Travel Dist',
                           'trigger': 'Trigger',
                           'battery': 'Battery',
                           'battery_status': 'Battery Status',
                           'gps_accuracy': 'GPS Accuracy',
                           'vertical_accuracy': 'Vertical Accuracy',
                           'badge': 'Badge',
                           'name': 'Name',
                           }

SENSOR_ATTR_ICON        = {'zone': 'mdi:cellphone-iphone',
                           'last_zone': 'mdi:cellphone-iphone',
                           'base_zone': 'mdi:cellphone-iphone',
                           'zone_timestamp': 'mdi:restore-clock',
                           'zone_distance': 'mdi:map-marker-distance',
                           'calc_distance': 'mdi:map-marker-distance',
                           'waze_distance': 'mdi:map-marker-distance',
                           'travel_time': 'mdi:clock-outline',
                           'dir_of_travel': 'mdi:compass-outline',
                           'interval': 'mdi:clock-start',
                           'info': 'mdi:information-outline',
                           'last_located': 'mdi:restore-clock',
                           'last_update': 'mdi:restore-clock',
                           'next_update': 'mdi:update',
                           'poll_count': 'mdi:counter',
                           'travel_distance': 'mdi:map-marker-distance',
                           'trigger': 'mdi:flash-outline',
                           'battery': 'mdi:battery',
                           'battery_status': 'mdi:battery',
                           'gps_accuracy': 'mdi:map-marker-radius',
                           'altitude': 'mdi:image-filter-hdr',
                           'vertical_accuracy': 'mdi:map-marker-radius',
                           'badge': 'mdi:shield-account',
                           'name': 'mdi:account',
                           'entity_log': 'mdi:format-list-checkbox',
                           }

SENSOR_ID_NAME_LIST     = {'zon': 'zone',
                           'zon1': 'zone_name1',
                           'zon2': 'zone_name2',
                           'zon3': 'zone_name3',
                           'bzon': 'base_zone',
                           'lzon': 'last_zone',
                           'lzon1': 'last_zone_name1',
                           'lzon2': 'last_zone_name2',
                           'lzon3': 'last_zone_name3',
                           'zonts': 'zone_timestamp',
                           'zdis': 'zone_distance',
                           'cdis': 'calc_distance',
                           'wdis': 'waze_distance',
                           'tdis': 'travel_distance',
                           'ttim': 'travel_time',
                           'dir': 'dir_of_travel',
                           'intvl':  'interval',
                           'lloc': 'last_located',
                           'lupdt': 'last_update',
                           'nupdt': 'next_update',
                           'cnt': 'poll_count',
                           'info': 'info',
                           'trig': 'trigger',
                           'bat': 'battery',
                           'batstat': 'battery_status',
                           'alt': 'altitude',
                           'gpsacc': 'gps_accuracy',
                           'vacc': 'vertical_accuracy',
                           'badge': 'badge',
                           'name': 'name',
                           }


ATTR_TIMESTAMP_FORMAT    = '%Y-%m-%d %H:%M:%S.%f'
APPLE_DEVICE_TYPES  = ['iphone', 'ipad', 'ipod', 'watch', 'iwatch', 'icloud',
                       'iPhone', 'iPad', 'iPod', 'Watch', 'iWatch', 'iCloud']
FMF_FAMSHR_LOCATION_FIELDS = ['altitude', 'latitude', 'longitude', 'timestamp',
                       'horizontalAccuracy', 'verticalAccuracy', 'batteryStatus']
#icloud_update commands
CMD_ERROR    = 1
CMD_INTERVAL = 2
CMD_PAUSE    = 3
CMD_RESUME   = 4
CMD_WAZE     = 5

#Other constants
IOSAPP_DT_ENTITY = True
ICLOUD_DT_ENTITY = False
ICLOUD_LOCATION_DATA_ERROR = False
#ICLOUD_LOCATION_DATA_ERROR = [False, 0, 0, '', HHMMSS_ZERO,
#                              0, 0, '', '', '', \
#                              False, HHMMSS_ZERO, 0, 0]
#General constants
HOME                    = 'home'
NOT_HOME                = 'not_home'
NOT_SET                 = 'not_set'
STATIONARY              = 'stationary'
AWAY_FROM               = 'AwayFrom'
AWAY                    = 'Away'
PAUSED                  = 'Paused'
STATIONARY_LAT_90       = 90
STATIONARY_LONG_180     = 180
STATIONARY_ZONE_VISIBLE = True
STATIONARY_ZONE_HIDDEN  = False
#STATIONARY_ZONE_HOME_OFFSET  = .00492   #(.5km) Subtract/add from home zone latitude to make stat zone location
STATIONARY_ZONE_HOME_OFFSET  = .00925   #(1km)   Subtract/add from home zone latitude to make stat zone location
EVENT_LOG_CLEAR_SECS    = 600           #Clear event log data interval
EVENT_LOG_CLEAR_CNT     = 15            #Number of recds to display when clearing event log
ICLOUD3_ERROR_MSG       = "ICLOUD3 ERROR-SEE EVENT LOG FOR MORE INFO"

#Devicename config parameter file extraction
DI_DEVICENAME           = 0
DI_DEVICE_TYPE          = 1
DI_NAME                 = 2
DI_EMAIL                = 3
DI_BADGE_PICTURE        = 4
DI_DEVICENAME_IOSAPP    = 5
DI_DEVICENAME_IOSAPP_ID = 6
DI_SENSOR_IOSAPP_TRIGGER= 7
DI_ZONES                = 8
DI_SENSOR_PREFIX_NAME   = 9

#Waze status codes
WAZE_REGIONS      = ['US', 'NA', 'EU', 'IL', 'AU']
WAZE_USED         = 0
WAZE_NOT_USED     = 1
WAZE_PAUSED       = 2
WAZE_OUT_OF_RANGE = 3
WAZE_NO_DATA      = 4

#Used by the 'update_method' in the polling_5_sec loop
IOSAPP_UPDATE     = 1
ICLOUD_UPDATE     = 2

#The event_log lovelace card will display the event in a special color if
#the text starts with a special character:
#    $   - MediumVioletRed   *   - #e600e6
#    $$  - DeepPink          **  - Fushia
#    $$$ - DarkGoldenRod     *** - OrangeRed
EVLOG_COLOR_STATS = "$$"
EVLOG_COLOR_DEBUG = "$$$"
EVLOG_COLOR_AUTHENTICATE = ""

#tracking_method config parameter being used
FMF               = 'fmf'       #Find My Friends
FAMSHR            = 'famshr'     #icloud Family-Sharing
IOSAPP            = 'iosapp'    #HA IOS App v1.5x or v2.x
IOSAPP1           = 'iosapp1'   #HA IOS App v1.5x only
FMF_FAMSHR        = [FMF, FAMSHR]
IOSAPP_IOSAPP1    = [IOSAPP, IOSAPP1]

TRK_METHOD_NAME = {
    'fmf': 'Find My Friends',
    'famshr': 'Family Sharing',
    'iosapp': 'IOS App',
    'iosapp1': 'IOS App v1',
}
TRK_METHOD_SHORT_NAME = {
    'fmf': 'FmF',
    'famshr': 'FamShr',
    'iosapp': 'IOSApp',
    'iosapp1': 'IOSApp1',
}
DEVICE_TYPE_FNAME = {
    'iphone': 'iPhone',
    'phone': 'iPhone',
    'ipad': 'iPad',
    'iwatch': 'iWatch',
    'watch': 'iWatch',
    'ipod': 'iPod',
}
IOS_TRIGGERS_VERIFY_LOCATION = ['Background Fetch',
                                'Initial',
                                'Manual',
                                'Significant Location Update',
                                'Push Notification',
                                'iOSApp Loc Update',
                                'Bkgnd Fetch',
                                'Sig Loc Update',
                                'iOSApp Loc Request',]
IOS_TRIGGERS_ENTER_ZONE      = ['Geographic Region Entered',
                                'iBeacon Region Entered'
                                'Geo Region Enter',
                                'iBeacon Enter',]
IOS_TRIGGERS_ENTER_EXIT_IC3  = ['Geographic Region Entered',
                                'Geographic Region Exited',
                                'iBeacon Region Entered'
                                'Geo Region Enter',
                                'Geo Region Exit',
                                'iBeacon Enter',]
IOS_TRIGGER_ABBREVIATIONS    = {'Geographic Region Entered': 'Geo Region Enter',
                                'Geographic Region Exited': 'Geo Region Exit',
                                'iBeacon Region Entered': 'iBeacon Enter',
                                'Significant Location Update': 'Sig Loc Update',
                                'Push Notification': 'iOSApp Loc Request',
                                'Background Fetch': 'Bkgnd Fetch',}


#Lists to hold the group names, group objects and iCloud device configuration
#The ICLOUD3_GROUPS is filled in on each platform load, the GROUP_OBJS is
#filled in after the polling timer is setup.
ICLOUD3_GROUPS     = []
ICLOUD3_GROUP_OBJS = {}
ICLOUD3_TRACKED_DEVICES = {}
'''
DEVICE_STATUS_SET = ['deviceModel', 'rawDeviceModel', 'deviceStatus',
                    'deviceClass', 'batteryLevel', 'id', 'lowPowerMode',
                    'deviceDisplayName', 'name', 'batteryStatus', 'fmlyShare',
                    'location',
                    'locationCapable', 'locationEnabled', 'isLocating',
                    'remoteLock', 'activationLocked', 'lockedTimestamp',
                    'lostModeCapable', 'lostModeEnabled', 'locFoundEnabled',
                    'lostDevice', 'lostTimestamp',
                    'remoteWipe', 'wipeInProgress', 'wipedTimestamp',
                    'isMac']
'''
#Default values are ["batteryLevel", "deviceDisplayName", "deviceStatus", "name"]
DEVICE_STATUS_SET = ['deviceClass', 'batteryStatus', 'lowPowerMode',
                     'location']

DEVICE_STATUS_CODES = {
    '200': 'online',
    '201': 'offline',
    '203': 'pending',
    '204': 'unregistered',
    '0': ''
}

SERVICE_SCHEMA = vol.Schema({
    vol.Optional(CONF_GROUP):  cv.slugify,
    vol.Optional(CONF_DEVICENAME): cv.slugify,
    vol.Optional(CONF_INTERVAL): cv.slugify,
    vol.Optional(CONF_COMMAND): cv.string
})

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_USERNAME): cv.string,
    vol.Optional(CONF_PASSWORD, default=''): cv.string,
    vol.Optional(CONF_GROUP, default='group'): cv.slugify,
    vol.Optional(CONF_TRACKING_METHOD, default='fmf'): cv.slugify,
    vol.Optional(CONF_MAX_IOSAPP_LOCATE_CNT, default=100): cv.string,
    vol.Optional(CONF_ENTITY_REGISTRY_FILE): cv.string,
    vol.Optional(CONF_CONFIG_IC3_FILE_NAME, default='config_ic3.yaml'): cv.string,

    #-----►►General Attributes ----------
    vol.Optional(CONF_UNIT_OF_MEASUREMENT, default='mi'): cv.slugify,
    vol.Optional(CONF_INZONE_INTERVAL, default='2 hrs'): cv.string,
    vol.Optional(CONF_CENTER_IN_ZONE, default=False): cv.boolean,
    vol.Optional(CONF_MAX_INTERVAL, default=0): cv.string,
    vol.Optional(CONF_TRAVEL_TIME_FACTOR, default=.60): cv.string,
    vol.Optional(CONF_GPS_ACCURACY_THRESHOLD, default=100): cv.string,
    vol.Optional(CONF_OLD_LOCATION_THRESHOLD, default='-1 min'): cv.string,
    vol.Optional(CONF_IGNORE_GPS_ACC_INZONE, default=True): cv.boolean,
    vol.Optional(CONF_HIDE_GPS_COORDINATES, default=False): cv.boolean,
    vol.Optional(CONF_LOG_LEVEL, default=''): cv.string,

    #-----►►Filter, Include, Exclude Devices ----------
    vol.Optional(CONF_TRACK_DEVICES, default=[]): vol.All(cv.ensure_list, [cv.string]),
    vol.Optional(CONF_TRACK_DEVICE, default=[]): vol.All(cv.ensure_list, [cv.string]),

    #-----►►Waze Attributes ----------
    vol.Optional(CONF_DISTANCE_METHOD, default='waze'): cv.string,
    vol.Optional(CONF_WAZE_REGION, default='US'): cv.string,
    vol.Optional(CONF_WAZE_MAX_DISTANCE, default=1000): cv.string,
    vol.Optional(CONF_WAZE_MIN_DISTANCE, default=1): cv.string,
    vol.Optional(CONF_WAZE_REALTIME, default=False): cv.boolean,

    #-----►►Other Attributes ----------
    vol.Optional(CONF_STATIONARY_INZONE_INTERVAL, default='30 min'): cv.string,
    vol.Optional(CONF_STATIONARY_STILL_TIME, default='8 min'): cv.string,
    vol.Optional(CONF_CREATE_SENSORS, default=[]): vol.All(cv.ensure_list, [cv.string]),
    vol.Optional(CONF_EXCLUDE_SENSORS, default=[]): vol.All(cv.ensure_list, [cv.string]),
    vol.Optional(CONF_COMMAND): cv.string,
    })

#==============================================================================
#
#   SYSTEM LEVEL FUNCTIONS
#
#==============================================================================
def _combine_lists(parm_lists):
    '''
    Take a list of lists and return a single list of all of the items.
        [['a,b,c'],['d,e,f']] --> ['a','b','c','d','e','f']
    '''
    new_list = []
    for lists in parm_lists:
        lists_items = lists.split(',')
        for lists_item in lists_items:
            new_list.append(lists_item)

    return new_list

#--------------------------------------------------------------------
def _test(parm1, parm2):
    return f"{parm1}-{parm2}"

#--------------------------------------------------------------------
def TRACE(desc, v1='+++', v2='', v3='', v4='', v5=''):
    '''
    Display a message or variable in the HA log file
    '''
    if desc != '':
        if v1 == '+++':
            value_str = f"►►TRACE►► {desc}"
        else:
            value_str = (f"►►TRACE►► {desc} = |{v1}|-|{v2}|-"
                         f"|{v3}|-|{v4}|-|{v5}|")
        _LOGGER.info(value_str)

#--------------------------------------------------------------------
def instr(string, find_string):
    if string == None or find_string == None:
        return False
    else:
        return string.find(find_string) >= 0

#--------------------------------------------------------------------
def isnumber(string):

    try:
        test_number = float(string)

        return True
    except:
        return False

#--------------------------------------------------------------------
def inlist(string, list_items):
    for item in list_items:
        if string.find(item) >= 0:
            return True

    return False

#--------------------------------------------------------------------
def format_gps(latitude, longitude, latitude_to=None, longitude_to=None):
    '''Format the GPS string for logs & messages'''
    gps = f"({round(latitude, 6)}, {round(longitude, 6)})"
    if latitude_to:
        gps += f" to ({round(latitude_to, 6)}, {round(longitude_to, 6)})"
    return gps
#==============================================================================
#
#   SETUP DEVICE_TRACKER SCANNER
#
#==============================================================================
def setup_scanner(hass, config: dict, see, discovery_info=None):
    """Set up the iCloud Scanner."""
    username              = config.get(CONF_USERNAME)
    password              = config.get(CONF_PASSWORD)
    #account_name         = config.get(CONF_ACCOUNT_NAME)
    group                 = config.get(CONF_GROUP)
    base_zone             = config.get(CONF_BASE_ZONE)
    tracking_method       = config.get(CONF_TRACKING_METHOD)
    track_devices         = config.get(CONF_TRACK_DEVICES)
    track_devices.extend(config.get(CONF_TRACK_DEVICE))
    log_level             = config.get(CONF_LOG_LEVEL)
    entity_registry_file  = config.get(CONF_ENTITY_REGISTRY_FILE)
    config_ic3_file_name  = config.get(CONF_CONFIG_IC3_FILE_NAME)
    max_iosapp_locate_cnt = int(config.get(CONF_MAX_IOSAPP_LOCATE_CNT))

    #make sure the same group is not specified in more than one platform. If so,
    #append with a number
    if group in ICLOUD3_GROUPS or group == 'group':
        group = f"{group}{len(ICLOUD3_GROUPS)+1}"
    ICLOUD3_GROUPS.append(group)
    ICLOUD3_TRACKED_DEVICES[group] = track_devices

    log_msg =(f"Setting up iCloud3 v{VERSION} device tracker for User: {username}, "
              f"Group: {group}")
    if HA_DEVICE_TRACKER_LEGACY_MODE:
        log_msg = (f"{log_msg}, using device_tracker.legacy code")
    _LOGGER.info(log_msg)

    if config.get(CONF_MAX_INTERVAL) == '0':
        inzone_interval_str = config.get(CONF_INZONE_INTERVAL)
    else:
        inzone_interval_str = config.get(CONF_MAX_INTERVAL)

    max_interval           = config.get(CONF_MAX_INTERVAL)
    center_in_zone_flag    = config.get(CONF_CENTER_IN_ZONE)
    gps_accuracy_threshold = config.get(CONF_GPS_ACCURACY_THRESHOLD)
    old_location_threshold_str = config.get(CONF_OLD_LOCATION_THRESHOLD)
    ignore_gps_accuracy_inzone_flag = config.get(CONF_IGNORE_GPS_ACC_INZONE)
    hide_gps_coordinates   = config.get(CONF_HIDE_GPS_COORDINATES)
    unit_of_measurement    = config.get(CONF_UNIT_OF_MEASUREMENT)

    stationary_inzone_interval_str = config.get(CONF_STATIONARY_INZONE_INTERVAL)
    stationary_still_time_str = config.get(CONF_STATIONARY_STILL_TIME)

    sensor_ids             = _combine_lists(config.get(CONF_CREATE_SENSORS))
    exclude_sensor_ids     = _combine_lists(config.get(CONF_EXCLUDE_SENSORS))

    travel_time_factor     = config.get(CONF_TRAVEL_TIME_FACTOR)
    waze_realtime          = config.get(CONF_WAZE_REALTIME)
    distance_method        = config.get(CONF_DISTANCE_METHOD).lower()
    waze_region            = config.get(CONF_WAZE_REGION)
    waze_max_distance      = config.get(CONF_WAZE_MAX_DISTANCE)
    waze_min_distance      = config.get(CONF_WAZE_MIN_DISTANCE)
    if waze_region not in WAZE_REGIONS:
        log_msg = (f"Invalid Waze Region ({waze_region}). Valid Values are: "
            "NA=US or North America, EU=Europe, IL=Isreal")
        _LOGGER.error(log_msg)

        waze_region       = 'US'
        waze_max_distance = 0
        waze_min_distance = 0

    '''
    TxRACE("group",group)
    TxRACE("base_zone",base_zone)
    TxRACE("tracking_method",tracking_method)
    TxRACE("track_devices",track_devices)
    TxRACE("entity_registry_file",entity_registry_file)
    TxRACE("max_iosapp_locate_cnt",max_iosapp_locate_cnt)
    TxRACE("inzone_interval_str",inzone_interval_str)
    TxRACE("center_in_zone_flag",center_in_zone_flag)
    TxRACE("gps_accuracy_threshold",gps_accuracy_threshold)
    TxRACE("old_location_threshold_str",old_location_threshold_str)
    TxRACE("stationary_inzone_interval_str",stationary_inzone_interval_str)
    TxRACE("stationary_still_time_str",stationary_still_time_str)
    TxRACE("ignore_gps_accuracy_inzone_flag",ignore_gps_accuracy_inzone_flag)
    TxRACE("hide_gps_coordinates",hide_gps_coordinates)
    TxRACE("sensor_ids",sensor_ids)
    TxRACE("exclude_sensor_ids",exclude_sensor_ids)
    TxRACE("unit_of_measurement",unit_of_measurement)
    TxRACE("travel_time_factor",travel_time_factor)
    TxRACE("distance_method",distance_method)
    TxRACE("waze_region",waze_region)
    TxRACE("waze_realtime",waze_realtime)
    TxRACE("waze_max_distance",waze_max_distance)
    TxRACE("waze_min_distance",waze_min_distance)
    TxRACE("log_level",log_level)
    '''

#---------------------------------------------
    #icloud_group =
    ICLOUD3_GROUP_OBJS[group] = Icloud3(
        hass, see, username, password, group, base_zone,
        tracking_method, track_devices,
        max_iosapp_locate_cnt, inzone_interval_str,
        center_in_zone_flag,
        gps_accuracy_threshold, old_location_threshold_str,
        stationary_inzone_interval_str, stationary_still_time_str,
        ignore_gps_accuracy_inzone_flag, hide_gps_coordinates,
        sensor_ids, exclude_sensor_ids,
        unit_of_measurement, travel_time_factor, distance_method,
        waze_region, waze_realtime, waze_max_distance, waze_min_distance,
        log_level,
        entity_registry_file, config_ic3_file_name
        )

    #ICLOUD3_GROUP_OBJS[group] = icloud_group


#--------------------------------------------------------------------

    def service_callback_update_icloud(call):
        """Call the update function of an iCloud group."""
        groups     = call.data.get(CONF_GROUP, ICLOUD3_GROUP_OBJS)
        devicename = call.data.get(CONF_DEVICENAME)
        command    = call.data.get(CONF_COMMAND)

        for group in groups:
            if group in ICLOUD3_GROUP_OBJS:
                ICLOUD3_GROUP_OBJS[group].service_handler_icloud_update(
                                    group, devicename, command)

    hass.services.register(DOMAIN, 'icloud3_update',
                service_callback_update_icloud, schema=SERVICE_SCHEMA)


#--------------------------------------------------------------------
    def service_callback__start_icloud3(call):
        """Reset an iCloud group."""
        groups = call.data.get(CONF_GROUP, ICLOUD3_GROUP_OBJS)
        for group in groups:
            if group in ICLOUD3_GROUP_OBJS:
                ICLOUD3_GROUP_OBJS[group]._start_icloud3()

    hass.services.register(DOMAIN, 'icloud3_restart',
                service_callback__start_icloud3, schema=SERVICE_SCHEMA)

#--------------------------------------------------------------------
    def service_callback_setinterval(call):
        """Call the update function of an iCloud group."""
        '''
        groups = call.data.get(CONF_GROUP, ICLOUD3_GROUP_OBJS)
        interval = call.data.get(CONF_INTERVAL)
        devicename = call.data.get(CONF_DEVICENAME)
        _LOGGER.warning("accounts=%s",accounts)
        _LOGGER.warning("devicename=%s",devicename)
        _LOGGER.warning("=%s",)

        for group in groups:
            if group in ICLOUD3_GROUP_OBJS:
                _LOGGER.warning("account=%s",account)
                ICLOUD3_GROUP_OBJS[group].service_handler_icloud_setinterval(
                                    account, interval, devicename)
        '''
        groups     = call.data.get(CONF_GROUP, ICLOUD3_GROUP_OBJS)
        interval   = call.data.get(CONF_INTERVAL)
        devicename = call.data.get(CONF_DEVICENAME)

        for group in groups:
            if group in ICLOUD3_GROUP_OBJS:
                ICLOUD3_GROUP_OBJS[group].service_handler_icloud_setinterval(
                                    group, interval, devicename)

    hass.services.register(DOMAIN, 'icloud3_set_interval',
                service_callback_setinterval, schema=SERVICE_SCHEMA)

#--------------------------------------------------------------------
    def service_callback_lost_iphone(call):
        """Call the lost iPhone function if the device is found."""
        groups = call.data.get(CONF_GROUP, ICLOUD3_GROUP_OBJS)
        devicename = call.data.get(CONF_DEVICENAME)
        for group in groups:
            if group in ICLOUD3_GROUP_OBJS:
                ICLOUD3_GROUP_OBJS[group].service_handler_lost_iphone(
                                    group, devicename)

    hass.services.register(DOMAIN, 'icloud3_lost_iphone',
                service_callback_lost_iphone, schema=SERVICE_SCHEMA)

    # Tells the bootstrapper that the component was successfully initialized
    return True


#====================================================================
class Icloud3(DeviceScanner):
    """Representation of an iCloud3 platform"""

    def __init__(self,
        hass, see, username, password, group, base_zone,
        tracking_method, track_devices,
        max_iosapp_locate_cnt, inzone_interval_str,
        center_in_zone_flag,
        gps_accuracy_threshold, old_location_threshold_str,
        stationary_inzone_interval_str, stationary_still_time_str,
        ignore_gps_accuracy_inzone_flag, hide_gps_coordinates,
        sensor_ids, exclude_sensor_ids,
        unit_of_measurement, travel_time_factor, distance_method,
        waze_region, waze_realtime, waze_max_distance, waze_min_distance,
        log_level,
        entity_registry_file, config_ic3_file_name
        ):


        """Initialize the iCloud3 device tracker."""
        self.hass_configurator_request_id    = {}

        self.hass                         = hass
        self.see                          = see
        self.username                     = username
        self.username_base                = username.split('@')[0]
        self.password                     = password

        self.api                          = None
        self.entity_registry_file         = entity_registry_file
        self.config_ic3_file_name         = config_ic3_file_name
        self.group                        = group
        self.base_zone                    = HOME
        self.verification_code            = None
        self.trusted_device               = None
        self.trusted_device_id            = None
        self.trusted_devices              = None
        self.valid_trusted_device_ids     = None
        self.tracking_method_config       = tracking_method

        self.max_iosapp_locate_cnt        = max_iosapp_locate_cnt
        self.start_icloud3_request_flag   = False
        self.start_icloud3_inprocess_flag = False
        self.authenticated_time           = 0
        self.log_level                    = log_level


        self.attributes_initialized_flag  = False
        self.track_devices                = track_devices
        self.distance_method_waze_flag    = (distance_method.lower() == 'waze')
        self.inzone_interval              = self._time_str_to_secs(inzone_interval_str)
        self.center_in_zone_flag          = center_in_zone_flag
        self.gps_accuracy_threshold       = int(gps_accuracy_threshold)
        self.old_location_threshold       = self._time_str_to_secs(old_location_threshold_str)
        self.ignore_gps_accuracy_inzone_flag = ignore_gps_accuracy_inzone_flag
        self.check_gps_accuracy_inzone_flag  = not self.ignore_gps_accuracy_inzone_flag
        self.hide_gps_coordinates         = hide_gps_coordinates
        self.sensor_ids                   = sensor_ids
        self.exclude_sensor_ids           = exclude_sensor_ids
        self.unit_of_measurement          = unit_of_measurement
        self.travel_time_factor           = float(travel_time_factor)
        self.e_seconds_local_offset_secs  = 0
        self.waze_region                  = waze_region
        self.waze_min_distance            = waze_min_distance
        self.waze_max_distance            = waze_max_distance
        self.waze_realtime                = waze_realtime
        self.stationary_still_time_str    = stationary_still_time_str
        self.stationary_inzone_interval_str = stationary_inzone_interval_str

        #define & initialize fields to carry across icloud3 restarts
        self._define_event_log_fields()
        self._define_usage_counters()

        #add HA event that will call the _polling_loop_5_sec_icloud function
        #on a 5-second interval. The interval is offset by 1-second for each
        #group to avoid update conflicts.
        self.start_icloud3_initial_load_flag = True
        if self._start_icloud3():
            track_utc_time_change(self.hass, self._polling_loop_5_sec_device,
                    second=[0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55])

        self.start_icloud3_initial_load_flag = False
#--------------------------------------------------------------------
    def _start_icloud3(self):
        """
        Start iCloud3, Define all variables & tables, Initialize devices
        """

        #check to see if restart is in process
        if self.start_icloud3_inprocess_flag:
            return

        try:
            start_timer = time.time()
            self.start_icloud3_inprocess_flag = True
            self.start_icloud3_request_flag   = False
            self.startup_log_msgs             = ''
            self.startup_log_msgs_prefix = NEW_LINE + '-'*55

            self._initialize_debug_control(self.log_level)
            self._initialize_um_formats(self.unit_of_measurement)
            self._define_device_fields()
            self._define_device_status_fields()
            self._define_device_tracking_fields()
            self._define_device_zone_fields()
            self._define_tracking_control_fields()
            self._setup_tracking_method(self.tracking_method_config)

            event_msg = (f"^^^ Initializing iCloud3 v{VERSION} > "
                         f"{dt_util.now().strftime('%A, %b %d')}")
            self._save_event_halog_info("*", event_msg)

            self.startup_log_msgs_prefix = NEW_LINE
            event_msg = (f"Stage 1 > Prepare iCloud3 for {self.username}")
            self._save_event_halog_info("*", event_msg)

            self._check_config_ic3_yaml_parameter_file()
            self._initialize_zone_tables()
            self._define_stationary_zone_fields(self.stationary_inzone_interval_str,
                        self.stationary_still_time_str)
            self._initialize_waze_fields(self.waze_region, self.waze_min_distance,
                        self.waze_max_distance, self.waze_realtime)

            for devicename in self.count_update_iosapp:
                self._display_usage_counts(devicename)

        except Exception as err:
            _LOGGER.exception(err)

        try:
            self.startup_log_msgs_prefix = NEW_LINE
            event_msg = (f"Stage 2 > Set up tracking method & identify devices")
            self._save_event_halog_info("*", event_msg)

            event_msg = (f"Preparing Tracking Method > {self.trk_method_name}")
            self._save_event_halog_info("*", event_msg)

            if self.TRK_METHOD_FMF_FAMSHR:
                self._initialize_pyicloud_device_api()

            self.this_update_secs     = self._time_now_secs()
            self.icloud3_started_secs = self.this_update_secs

            self._setup_tracked_devices_config_parm(self.track_devices)
            self._define_sensor_fields(self.start_icloud3_initial_load_flag)

            if self.TRK_METHOD_FMF:
                self._setup_tracked_devices_for_fmf()

            elif self.TRK_METHOD_FAMSHR:
                self._setup_tracked_devices_for_famshr()

            if self.TRK_METHOD_IOSAPP:
                self._setup_tracked_devices_for_iosapp()

        except Exception as err:
            _LOGGER.exception(err)

        try:
            self.startup_log_msgs_prefix = NEW_LINE
            event_msg = (f"Stage 3 > Verify tracked devices")
            self._save_event_halog_info("*", event_msg)

            self.track_devicename_list == ''
            for devicename in self.devicename_verified:
                error_log_msg = None

                #Devicename config parameter is OK, now check to make sure the
                #entity for device name has been setup by iosapp correctly.
                #If the devicename is valid, it will be tracked
                if self.devicename_verified.get(devicename):
                    self.tracking_device_flag[devicename] = True
                    self.tracked_devices.append(devicename)

                    self.track_devicename_list = (f"{self.track_devicename_list}, {devicename}")
                    if self.iosapp_version.get(devicename) == 2:
                        self.track_devicename_list = (f"{self.track_devicename_list} "
                                f"({self.devicename_iosapp.get(devicename)})")
                    event_msg = (f"Verified Device > "
                        f"{self._format_fname_devicename(devicename)}")
                    self._save_event_halog_info("*", event_msg)

                #If the devicename is not valid, it will not be tracked
                elif self.TRK_METHOD_FMF_FAMSHR:
                    event_msg = (f"iCloud3 Error for {self._format_fname_devicename(devicename)}/{devicename} > "
                        f"The iCloud Account for {self.username} did not return any "
                        f"device information for this device when setting up "
                        f"{self.trk_method_name}."
                        f"CRLF 1. Restart iCloud3 on the Event_log "
                        f"screen or restart HA."
                        f"CRLF 2. Verify the devicename on the track_devices "
                        f"parameter if the error persists."
                        f"CRLF 3. Refresh the Event Log in your "
                        f"browser to refresh the list of devices.")
                    self._save_event_halog_error("*", event_msg)

                else:
                    event_msg = (f"Not Tracking Device > "
                        f"{self._format_fname_devicename(devicename)}")
                    self._save_event_halog_info("*", event_msg)

                if error_log_msg:
                    self._save_event_halog_error("*", event_msg)
                    self._save_event_halog_error("*", error_log_msg)

                else:
                    if self.iosapp_version.get(devicename) == 1:
                        event_msg = (f"IOS App v1 monitoring > device_tracker.{devicename}")
                        self._save_event_halog_info("*", event_msg)
                    elif self.iosapp_version.get(devicename) == 2:
                        event_msg = (f"IOS App v2 monitoring > "
                                     f"device_tracker.{self.devicename_iosapp.get(devicename)}, "
                                     f"sensor.{self.iosapp_v2_last_trigger_entity.get(devicename)}")
                        self._save_event_halog_info("*", event_msg)

            #Now that the devices have been set up, finish setting up
            #the Event Log Sensor
            self._setup_event_log_base_attrs(self.start_icloud3_initial_load_flag)
            self._setup_sensors_custom_list(self.start_icloud3_initial_load_flag)

            #nothing to do if no devices to track
            if self.track_devicename_list == '':
                event_msg = (f"iCloud3 Error for {self.username} > No devices to track. "
                    f"Setup aborted. Check `track_devices` parameter and verify the "
                    f"device name matches the iPhone Name on the `Settings>General>About` "
                    f"screen on the devices to be tracked.")
                self._save_event_halog_error("*", event_msg)

                self._update_event_log_sensor_line_items("*")
                return False

            self.track_devicename_list = (f"{self.track_devicename_list[1:]}")
            event_msg = (f"Tracking Devices > {self.track_devicename_list}")
            self._save_event_halog_info("*", event_msg)

            self.startup_log_msgs_prefix = NEW_LINE
            event_msg = (f"Stage 4 > Configure valid tracked devices")
            self._save_event_halog_info("*", event_msg)

            for devicename in self.tracked_devices:
                if len(self.track_from_zone.get(devicename)) > 1:
                    w = str(self.track_from_zone.get(devicename))
                    w = w.replace("[", "")
                    w = w.replace("]", "")
                    w = w.replace("'", "")
                    event_msg = (f"Tracking from zones > {w}")
                    self._save_event_halog_info("*", event_msg)

                self._initialize_device_status_fields(devicename)
                self._initialize_device_tracking_fields(devicename)
                self._initialize_usage_counters(devicename, self.start_icloud3_initial_load_flag)
                self._initialize_device_zone_fields(devicename)
                self._setup_sensor_base_attrs(devicename, self.start_icloud3_initial_load_flag)

                #check to see if devicename's stationary zone already exists
                #if so, use that location. If not, use home zone +.0005
                zone_name = self._format_zone_name(devicename, STATIONARY)
                if zone_name in self.zone_lat:
                    latitude  = self.zone_lat.get(zone_name)
                    longitude = self.zone_long.get(zone_name)
                else:
                    latitude  = self.stat_zone_base_lat
                    longitude = self.stat_zone_base_long

                self._update_stationary_zone(
                    devicename,
                    latitude,
                    longitude,
                    STATIONARY_ZONE_HIDDEN)
                self.in_stationary_zone_flag[devicename] = False


                #Initialize the new attributes
                kwargs = self._setup_base_kwargs(devicename,
                            self.zone_home_lat, self.zone_home_long, 0, 0)
                attrs  = self._initialize_attrs(devicename)

                self._update_device_attributes(
                    devicename,
                    kwargs,
                    attrs,
                    '_start_icloud3')

                if self.start_icloud3_initial_load_flag:
                    self._update_device_sensors(devicename, kwargs)
                    self._update_device_sensors(devicename, attrs)

            self._update_event_log_sensor_line_items(self.tracked_devices[0])

            #Everying reset. Now do an iCloud update to set up the device info.
            self.startup_log_msgs_prefix = NEW_LINE
            event_msg = (f"Stage 5 > Locating tracked devices")
            self._save_event_halog_info("*", event_msg)

            if self.TRK_METHOD_FMF_FAMSHR:
                self.start_icloud3_inprocess_flag = False
                self._refresh_pyicloud_devices_location_data(HIGH_INTEGER, devicename)

                self._update_device_icloud('Initial Locate')
                self.start_icloud3_inprocess_flag = True

        except Exception as err:
            _LOGGER.exception(err)

        for devicename in self.tracked_devices:
            if self.log_level_debug_flag or self.log_level_eventlog_flag:
                self._display_usage_counts(devicename, force_display=(not self.start_icloud3_initial_load_flag))

        self.startup_log_msgs_prefix = NEW_LINE
        event_msg = (f"^^^ Initializing iCloud3 v{VERSION} > Complete, "
                     f"Took {round(time.time()-start_timer, 2)} sec")
        self._save_event_halog_info("*", event_msg)

        self.start_icloud3_inprocess_flag = False

        self.startup_log_msgs_prefix = NEW_LINE + '-'*55
        self.startup_log_msgs = self.startup_log_msgs.replace("CRLF", NEW_LINE)
        _LOGGER.info(self.startup_log_msgs)
        self.startup_log_msgs = ''

        return True

#########################################################
#
#   This function is called every 5 seconds by HA. Cycle through all
#   of the iCloud devices to see if any of the ones being tracked need
#   to be updated. If so, we might as well update the information for
#   all of the devices being tracked since PyiCloud gets data for
#   every device in the account
#
#########################################################
    def _polling_loop_5_sec_device(self, now):
        try:
            fct_name = "_polling_loop_5_sec_device"

            if self.start_icloud3_request_flag:    #via service call
                self._start_icloud3()

            elif self.any_device_being_updated_flag:
                return

        except Exception as err:
            _LOGGER.exception(err)
            return

        self.this_update_secs = self._time_now_secs()
        count_reset_timer     = dt_util.now().strftime('%H:%M:%S')
        this_minute           = int(dt_util.now().strftime('%M'))
        this_5sec_loop_second = int(dt_util.now().strftime('%S'))

        #Reset counts on new day, check for daylight saving time new offset
        if count_reset_timer.endswith(':00:00'):
            self._timer_tasks_every_hour()

        if count_reset_timer == HHMMSS_ZERO:
            self._timer_tasks_midnight()

        elif count_reset_timer == '01:00:00':
            self._timer_tasks_1am()

        try:
            if self.this_update_secs >= self.event_log_clear_secs and \
                        self.log_level_debug_flag == False:
                self._update_event_log_sensor_line_items('clear_log_items')

            for devicename in self.tracked_devices:
                devicename_zone = self._format_devicename_zone(devicename, HOME)

                if (self.tracking_device_flag.get(devicename) is False or
                        self.next_update_time.get(devicename_zone) == PAUSED):
                    continue

                update_method     = None
                self.state_change_flag[devicename] = False

                #get tracked_device (device_tracker.<devicename>) state & attributes
                #icloud & ios app v1 use this entity
                entity_id = self.device_tracker_entity.get(devicename)
                state     = self._get_state(entity_id)

                #Will be not_set with a last_poll value if the iosapp has not be set up
                if state == NOT_SET and self.state_last_poll.get(devicename) != NOT_SET:
                    self._request_iosapp_location_update(devicename)
                    continue

                dev_attrs          = self._get_device_attributes(entity_id)
                #Extract only attrs needed to update the device
                dev_attrs_avail    = {k: v for k, v in dev_attrs.items() if k in DEVICE_ATTRS_BASE}
                dev_data           = {**DEVICE_ATTRS_BASE, **dev_attrs_avail}

                dev_latitude       = dev_data[ATTR_LATITUDE]
                dev_longitude      = dev_data[ATTR_LONGITUDE]
                dev_gps_accuracy   = dev_data[ATTR_GPS_ACCURACY]
                dev_battery        = dev_data[ATTR_BATTERY_LEVEL]
                dev_trigger        = dev_data[ATTR_TRIGGER]
                dev_timestamp_secs = self._timestamp_to_secs(dev_data[ATTR_TIMESTAMP])
                v2_dev_attrs       = None

                #iosapp v2 uses the device_tracker.<devicename>_# entity for
                #location info and sensor.<devicename>_last_update_trigger entity
                #for trigger info. Get location data and trigger.
                #Use the trigger/timestamp if timestamp is newer than current
                #location timestamp.

                update_reason      = ""
                ios_update_reason  = ""
                update_via_v2_flag = False

                if self.iosapp_version.get(devicename) == 2:
                    entity_id    = self.device_tracker_entity_iosapp.get(devicename)
                    v2_state     = self._get_state(entity_id)
                    v2_dev_attrs = self._get_device_attributes(entity_id)

                    if ATTR_LATITUDE not in v2_dev_attrs:
                        self.iosapp_version[devicename] = 1
                        event_msg = (f"iCloud3 Error > IOS App v2 Entity {entity_id} does not "
                            "contain location attributes (latitude, longitude). Try the following:"
                            "CRLF 1. Refresh & restart IOS App on device, "
                            "request a Manual Refresh."
                            "CRLF 2. Check Developer Tools>States "
                            "entity for location attributes."
                            "CRLF 3. Check HA integrations for the entity."
                            "CRLF 4. Restart HA or issue "
                            "'device_tracker.icloud3_reset' Service Call "
                            "reverting to IOS App v1.")
                        self._save_event_halog_error(devicename, event_msg)
                        continue

                    v2_state_changed_time, v2_state_changed_secs, v2_state_changed_timestamp = \
                            self._get_entity_last_changed_time(entity_id)

                    v2_trigger,  v2_trigger_changed_time, v2_trigger_changed_secs = \
                            self._get_iosappv2_device_sensor_trigger(devicename)

                    #Initialize if first time through
                    if self.last_v2_trigger.get(devicename) == '':
                        self.last_v2_state[devicename]                = v2_state
                        self.last_v2_state_changed_time[devicename]   = v2_state_changed_time
                        self.last_v2_state_changed_secs[devicename]   = v2_state_changed_secs
                        self.last_v2_trigger[devicename]              = v2_trigger
                        self.last_v2_trigger_changed_time[devicename] = v2_trigger_changed_time
                        self.last_v2_trigger_changed_secs[devicename] = v2_trigger_changed_secs

                        if self.TRK_METHOD_IOSAPP:
                            update_via_v2_flag = True
                            ios_update_reason = "Initial Locate"

                    #State changed
                    elif v2_state != self.last_v2_state.get(devicename):
                        update_via_v2_flag = True
                        ios_update_reason = (f"State Change-{v2_state}")

                    #Prevent duplicate update if State & Trigger changed at the same time
                    #and state change was handled on last cycle
                    elif (v2_trigger != self.last_v2_trigger.get(devicename)):
                        if v2_trigger_changed_secs == v2_state_changed_secs:
                            self.last_v2_trigger[devicename] = v2_trigger
                        else:
                            update_via_v2_flag = True
                            ios_update_reason  = (f"Trigger Change-{v2_trigger}")

                    #State changed more than 5-secs after last locate
                    elif v2_state_changed_secs > (self.last_located_secs.get(devicename) + 5):
                        update_via_v2_flag = True
                        v2_trigger = "iOSApp Loc Update"
                        v2_trigger_changed_secs = v2_state_changed_secs
                        ios_update_reason = (f"iOSApp Loc Update@{v2_state_changed_time}")

                    #Trigger changed more than 5-secs after last locate
                    elif (v2_trigger_changed_secs > (self.last_v2_trigger_changed_secs.get(devicename) + 5)):
                        update_via_v2_flag = True
                        ios_update_reason = (f"Trigger Time@{self._secs_to_time(v2_trigger_changed_secs)}")

                    #Bypass if trigger contains ic3 date stamp suffix (@hhmmss)
                    elif instr(v2_trigger, '@'):
                        ios_update_reason = (f"Status")
                        pass

                    if state != v2_state or dev_trigger != v2_trigger:
                        v2_trigger_msg = v2_trigger if instr(v2_trigger, "*") else \
                                (f"{v2_trigger}@{self._secs_to_time(v2_trigger_changed_secs)}")

                        iosapp_msg = (f"iOSApp Monitor > "
                            f"State-{self.last_v2_state.get(devicename)} to {v2_state}, "
                            f"Trigger-{dev_trigger} to {v2_trigger_msg}, "
                            f"GPS-{format_gps(v2_dev_attrs[ATTR_LATITUDE], v2_dev_attrs[ATTR_LONGITUDE])}, "
                            f"LastLocated-{self.last_located_time.get(devicename)}")
                        #if ((update_via_v2_flag and iosapp_msg != self.last_iosapp_msg.get(devicename)) and
                        #        self.last_iosapp_msg.get(devicename) != ''):
                        self.log_debug_msg(devicename, iosapp_msg)
                        self._save_event(devicename, iosapp_msg)
                        #self.last_iosapp_msg[devicename] = iosapp_msg


                    if update_via_v2_flag:
                        age                          = v2_trigger_changed_secs - self.this_update_secs
                        state                        = v2_state
                        dev_latitude                 = v2_dev_attrs[ATTR_LATITUDE]
                        dev_longitude                = v2_dev_attrs[ATTR_LONGITUDE]
                        dev_gps_accuracy             = v2_dev_attrs[ATTR_GPS_ACCURACY]
                        dev_battery                  = v2_dev_attrs[ATTR_BATTERY_LEVEL]
                        dev_trigger                  = v2_trigger
                        dev_timestamp_secs           = v2_trigger_changed_secs
                        dev_data[ATTR_LATITUDE]      = dev_latitude
                        dev_data[ATTR_LONGITUDE]     = dev_longitude
                        dev_data[ATTR_TIMESTAMP]     = v2_state_changed_timestamp
                        dev_data[ATTR_GPS_ACCURACY]  = dev_gps_accuracy
                        dev_data[ATTR_BATTERY_LEVEL] = dev_battery
                        dev_data[ATTR_ALTITUDE]      = self._get_attr(v2_dev_attrs, ATTR_ALTITUDE, NUMERIC)
                        dev_data[ATTR_VERT_ACCURACY] = \
                                self._get_attr(v2_dev_attrs, ATTR_VERT_ACCURACY, NUMERIC)

                        self.last_v2_state[devicename]                = v2_state
                        self.last_v2_state_changed_time[devicename]   = v2_state_changed_time
                        self.last_v2_state_changed_secs[devicename]   = v2_state_changed_secs
                        self.last_v2_trigger[devicename]              = v2_trigger
                        self.last_v2_trigger_changed_time[devicename] = v2_trigger_changed_time
                        self.last_v2_trigger_changed_secs[devicename] = v2_trigger_changed_secs


                #Add update time onto trigger if it is not there already. IOS App
                #will wipe time out and cause an update to occur.
                self.last_located_secs[devicename] = dev_timestamp_secs
                zone = self._format_zone_name(devicename, state)

                if (self.TRK_METHOD_IOSAPP and
                        self.zone_current.get(devicename) == ''):
                    update_method = IOSAPP_UPDATE
                    update_reason = ("Initial Locate")

                #device_tracker.see svc all from automation wipes out
                #latitude and longitude. Reset via icloud update.
                elif dev_latitude == 0:
                    update_method = ICLOUD_UPDATE
                    self.next_update_secs[devicename_zone] = 0

                    update_reason = \
                        (f"GPS data = 0 {self.state_last_poll.get(devicename)}-{state}")
                    dev_trigger = "RefreshLocation"

                #Update the device if it wasn't completed last time.
                elif (self.state_last_poll.get(devicename) == NOT_SET):
                    update_method = ICLOUD_UPDATE
                    dev_trigger   = "RetryUpdate"
                    update_reason = ("Last Update not completed, retrying")
                    self._save_event(devicename, update_reason)

                #The state can be changed via device_tracker.see service call
                #with a different location_name in an automation or by an
                #ios app notification that a zone is entered or exited. If
                #by the ios app, the trigger is 'Geographic Region Exited' or
                #'Geographic Region Entered'. In iosapp 2.0, the state is
                #changed without a trigger being posted and will be picked
                #up here anyway.
                elif (state != self.state_last_poll.get(devicename)):
                    self.state_change_flag[devicename] = True
                    update_method = IOSAPP_UPDATE
                    self.count_state_changed[devicename] += 1
                    update_reason = "State Change"
                    event_msg     = (f"State Change detected > "
                                    f"{self.state_last_poll.get(devicename)} to "
                                     f"{state}")
                    self._save_event(devicename, event_msg)

                elif dev_trigger != self.trigger.get(devicename):
                    update_method = IOSAPP_UPDATE
                    self.count_trigger_changed[devicename] += 1
                    update_reason = "Trigger Change"
                    event_msg     = (f"Trigger Change detected > "
                                     f"{dev_trigger}@{self._secs_to_time(v2_trigger_changed_secs)}")
                    self._save_event(devicename, event_msg)

                else:
                    update_reason = f"IgnoredTtrigger-{dev_trigger}"

                self.trigger[devicename] = dev_trigger

                #If exit trigger flag is not set, set it now if Exiting zone
                #If already set, leave it alone and reset when enter Zone (v2.1x)
                if (update_method == IOSAPP_UPDATE and
                        self.got_exit_trigger_flag.get(devicename) == False):
                    self.got_exit_trigger_flag[devicename] = instr(dev_trigger, 'Exit')


                #Update because of state or trigger change.
                #Accept the location data as it was sent by ios if the trigger
                #is for zone enter, exit, manual or push notification,
                #or if the last trigger was already handled by ic3 ( an '@hhmmss'
                #was added to it.
                #If the trigger was sometning else (Significant Location Change,
                #Background Fetch, etc, check to make sure it is not old or
                #has poor gps info.
                if update_method == IOSAPP_UPDATE:
                    #self._trace_device_attributes(
                    #        devicename, '5sPoll', update_reason, dev_attrs)

                    dist_from_zone_m = self._zone_distance_m(
                                devicename,
                                zone,
                                dev_latitude,
                                dev_longitude)

                    zone_radius_m = self.zone_radius_m.get(
                                zone,
                                self.zone_radius_m.get(HOME))
                    zone_radius_accuracy_m = zone_radius_m + self.gps_accuracy_threshold

                    if dev_trigger in IOS_TRIGGERS_ENTER_ZONE:
                        if (zone in self.zone_lat and
                                dist_from_zone_m > self.zone_radius_m.get(zone)*2 and
                                dist_from_zone_m < HIGH_INTEGER):
                            event_msg = (f"Conflicting enter zone trigger, Moving into zone > "
                                f"Zone-{zone}, Distance-{dist_from_zone_m} m, "
                                f"ZoneVerifyDist-{self.zone_radius_m.get(zone)*2} m, "
                                f"GPS-({format_gps(dev_latitude, dev_longitude)}")
                            self._save_event_halog_info(devicename, event_msg)

                            dev_latitude             = self.zone_lat.get(zone)
                            dev_longitude            = self.zone_long.get(zone)
                            dev_data[ATTR_LATITUDE]  = dev_latitude
                            dev_data[ATTR_LONGITUDE] = dev_longitude

                    #Check info if Background Fetch, Significant Location Update,
                    #Push, Manual, Initial
                    elif (dev_trigger in IOS_TRIGGERS_VERIFY_LOCATION):
                        old_loc_poor_gps_flag = self._check_old_loc_poor_gps(
                                devicename,
                                dev_timestamp_secs,
                                dev_gps_accuracy)

                        #If old location, discard
                        if old_loc_poor_gps_flag:
                            update_method     = None
                            ios_update_reason = None
                            location_age      = self._secs_since(dev_timestamp_secs)

                            event_msg = (f"Discarding > Old location or poor GPS, "
                                    f"Located-{self._secs_to_time(dev_timestamp_secs)} "
                                    f"({self._secs_to_time_str(location_age)} ago), "
                                    f"GPS-{format_gps(dev_latitude, dev_longitude)}, "
                                    f"GPSAccuracy-{dev_gps_accuracy}, "
                                    f"OldLocThreshold-{self._secs_to_time_str(self.old_location_secs.get(devicename))}")
                            self._save_event_halog_debug(devicename, event_msg)

                        #If got these triggers and not old location check a few
                        #other things
                        else:
                            update_reason = (f"{dev_trigger}")
                            self.last_iosapp_trigger[devicename] = dev_trigger

                            #if the zone is a stationary zone and no exit trigger,
                            #the zones in the ios app may not be current.
                            if (dist_from_zone_m >= zone_radius_m * 2 and
                                    instr(zone, STATIONARY) and
                                    instr(self.zone_last.get(devicename), STATIONARY)):
                                event_msg = ("Outside Stationary Zone without "
                                    "Exit Trigger > Check iOS App Configuration/"
                                    "Location for stationary zones. Force app "
                                    "refresh to reload zones if necessary. "
                                    f"Distance-{dist_from_zone_m} m, "
                                    f"StatZoneTestDist-{zone_radius_m * 2} m")
                                self._save_event_halog_info(devicename, event_msg)

                                self.iosapp_stat_zone_action_msg_cnt[devicename] += 1
                                if self.iosapp_stat_zone_action_msg_cnt.get(devicename) < 5:
                                    entity_id = self.notify_iosapp_entity.get(devicename)
                                    service_data = {
                                        "title": "iCloud3/iOSApp Zone Action Needed",
                                        "message": "The iCloud3 Stationary Zone may "\
                                            "not be loaded in the iOSApp. Force close "\
                                            "the iOSApp from the iOS App Switcher. "\
                                            "Then restart the iOSApp to reload the HA zones. "\
                                            f"Distance-{dist_from_zone_m} m, "
                                            f"StatZoneTestDist-{zone_radius_m * 2} m",
                                        "data": {"subtitle": "Stationary Zone Exit "\
                                            "Trigger was not received"}}
                                    self.hass.services.call("notify", entity_id, service_data)

                            #Check to see if currently in a zone. If so, check the zone distance.
                            #If new location is outside of the zone and inside radius*4, discard
                            #by treating it as poor GPS
                            if self._is_inzoneZ(zone):
                                outside_no_exit_trigger_flag, info_msg = \
                                    self._check_outside_zone_no_exit(devicename, zone,
                                            dev_latitude, dev_longitude)
                                if outside_no_exit_trigger_flag:
                                    update_method     = None
                                    ios_update_reason = None
                                    self._save_event_halog_info(devicename, info_msg)

                            #update via icloud to verify location if less than home_radius*10
                            elif (dist_from_zone_m <= zone_radius_m * 10 and
                                    self.TRK_METHOD_FMF_FAMSHR):
                                event_msg = (f"iCloud being called to verify location > "
                                    f"Zone-{zone}, "
                                    f"Distance-{self._format_dist_m(dist_from_zone_m)}, "
                                    f"ZoneVerifyDist-{self._format_dist_m(zone_radius_m*10)}, "
                                    f"GPS-{format_gps(dev_latitude, dev_longitude)}")
                                self._save_event_halog_info(devicename, event_msg)
                                update_method = ICLOUD_UPDATE

                    if (dev_data[ATTR_LATITUDE] == None or dev_data[ATTR_LONGITUDE] == None):
                        update_method = ICLOUD_UPDATE

                if update_method == IOSAPP_UPDATE:
                    self.state_this_poll[devicename]    = state
                    self.iosapp_update_flag[devicename] = True

                    update_method = self._update_device_iosapp(devicename, update_reason, dev_data)
                    self.any_device_being_updated_flag = False

                if update_method == ICLOUD_UPDATE and self.TRK_METHOD_FMF_FAMSHR:
                    self._update_device_icloud(devicename, update_reason)

                #If less than 90 secs to the next update for any devicename:zone, display time to
                #the next update in the NextUpdt time field, e.g, 1m05s or 0m15s.
                if devicename in self.track_from_zone:
                    for zone in self.track_from_zone.get(devicename):
                        devicename_zone = self._format_devicename_zone(devicename, zone)
                        if devicename_zone in self.next_update_secs:
                            age_secs = self._secs_to(self.next_update_secs.get(devicename_zone))
                            if (age_secs <= 90 and age_secs >= -15):
                                self._display_time_till_update_info_msg(
                                    devicename_zone,
                                    age_secs)

                if update_method != None:
                    self.device_being_updated_flag[devicename] = False
                    self.state_change_flag[devicename]         = False
                    self.log_debug_msgs_trace_flag             = False
                    self.update_in_process_flag                = False

        except Exception as err:
            _LOGGER.exception(err)
            log_msg = (f"Device Update Error, Error-{ValueError}")
            self.log_error_msg(log_msg)

        self.update_in_process_flag    = False
        self.log_debug_msgs_trace_flag = False

        #Cycle thru all devices and check to see if devices next update time
        #will occur in 5-secs. If so, request a location update now so it
        #it might be current on the next update.
        if ((this_5sec_loop_second % 15) == 10):
            self._polling_loop_10_sec_fmf_loc_prefetch(now)

        #Cycle thru all devices and check to see if devices need to be
        #updated via every 15 seconds
        if ((this_5sec_loop_second % 15) == 0) and self.TRK_METHOD_FMF_FAMSHR:
            self._polling_loop_15_sec_icloud(now)

#--------------------------------------------------------------------
    def _retry_update(self, devicename):
        #This flag will be 'true' if the last update for this device
        #was not completed. Do another update now.
        self.device_being_updated_retry_cnt[devicename] = 0
        while (self.device_being_updated_flag.get(devicename) and
            self.device_being_updated_retry_cnt.get(devicename) < 4):
            self.device_being_updated_retry_cnt[devicename] += 1

            log_msg = (f"{self._format_fname_devtype(devicename)} "
                f"Retrying Update, Update was not completed in last cycle, "
                f"Retry #{self.device_being_updated_retry_cnt.get(devicename)}")
            self._save_event_halog_info(devicename, log_msg)

            self.device_being_updated_flag[devicename] = True
            self.log_debug_msgs_trace_flag = True

            self._wait_if_update_in_process()
            update_reason = (f"Retry Update #{self.device_being_updated_retry_cnt.get(devicename)}")

            self._update_device_icloud(update_reason, devicename)

#########################################################
#
#   Update the device on a state or trigger change was recieved from the ios app
#     ●►●◄►●▬▲▼◀►►●◀ oPhone=►▶
#########################################################
    def _update_device_iosapp(self, devicename, update_reason, dev_data):
        """

        """

        if self.start_icloud3_inprocess_flag:
            return

        fct_name = "_update_device_ios_trigger"

        self.any_device_being_updated_flag = True
        return_code = IOSAPP_UPDATE

        try:
            devicename_zone = self._format_devicename_zone(devicename, HOME)

            if self.next_update_time.get(devicename_zone) == PAUSED:
                return

            latitude  = dev_data[ATTR_LATITUDE]
            longitude = dev_data[ATTR_LONGITUDE]

            if latitude == None or longitude == None:
                return

            iosapp_version_text = (f"ios{self.iosapp_version.get(devicename)}")

            event_msg = (f"iOS App v{self.iosapp_version.get(devicename)} update started "
                         f"({update_reason.split('@')[0]})")
            self._save_event(devicename, event_msg)

            self.update_timer[devicename] = time.time()

            entity_id     = self.device_tracker_entity.get(devicename)
            state = self._get_state(entity_id)

            self._log_start_finish_update_banner('▼▼▼', devicename,
                            iosapp_version_text, update_reason)

            self._trace_device_attributes(devicename, 'dev_data', fct_name, dev_data)


            timestamp = self._timestamp_to_time(dev_data[ATTR_TIMESTAMP])

            if timestamp == HHMMSS_ZERO:
                timestamp = self._secs_to_time(self.this_update_secs)

            gps_accuracy   = dev_data[ATTR_GPS_ACCURACY]
            battery        = dev_data[ATTR_BATTERY_LEVEL]
            battery_status = dev_data[ATTR_BATTERY_STATUS]
            device_status  = dev_data[ATTR_DEVICE_STATUS]
            low_power_mode = dev_data[ATTR_LOW_POWER_MODE]
            vertical_accuracy = self._get_attr(dev_data, ATTR_VERT_ACCURACY, NUMERIC)
            altitude       = self._get_attr(dev_data, ATTR_ALTITUDE, NUMERIC)

            location_isold_attr = False
            location_isold_flag = False
            self.old_loc_poor_gps_cnt[devicename] = 0
            self.old_loc_poor_gps_msg[devicename] = False
            attrs = {}

            #--------------------------------------------------------
            try:
                if self.device_being_updated_flag.get(devicename):
                    info_msg = "Last update not completed, retrying"
                else:
                    info_msg = "Updating"
                info_msg = (f"● {info_msg} {self.fname.get(devicename)} ●")

                self._display_info_status_msg(devicename, info_msg)
                self.device_being_updated_flag[devicename] = True

            except Exception as err:
                _LOGGER.exception(err)
                attrs = self._internal_error_msg(
                        fct_name, err, 'UpdateAttrs1')

            try:
                for zone in self.track_from_zone.get(devicename):
                    #If the state changed, only process the zone that changed
                    #to avoid delays caused calculating travel time by other zones
                    if (self.state_change_flag.get(devicename) and
                        self.state_this_poll.get(devicename) != zone and
                        zone != HOME):
                        continue

                    #discard trigger if outsize zone with no exit trigger
                    if self._is_inzoneZ(zone):
                        discard_flag, discard_msg = \
                            self._check_outside_zone_no_exit(devicename, zone, latitude, longitude)

                        if discard_flag:
                            self._save_event(devicename, discard_msg)
                            continue

                    self._set_base_zone_name_lat_long_radius(zone)
                    self._log_start_finish_update_banner('▼-▼', devicename,
                            iosapp_version_text, zone)

                    attrs = self._determine_interval(
                        devicename,
                        latitude,
                        longitude,
                        battery,
                        gps_accuracy,
                        location_isold_flag,
                        self.last_located_secs.get(devicename),
                        timestamp,
                        iosapp_version_text)

                    if attrs != {}:
                        self._update_device_sensors(devicename, attrs)
                    self._log_start_finish_update_banner('▲-▲', devicename,
                            iosapp_version_text, zone)

            except Exception as err:
                attrs = self._internal_error_msg(fct_name, err, 'DetInterval')
                self.any_device_being_updated_flag = False
                return ICLOUD_UPDATE

            try:
                #attrs should not be empty, but catch it and do an icloud update
                #if it is and no data is available. Exit without resetting
                #device_being_update_flag so an icloud update will be done.
                if attrs == {} and self.TRK_METHOD_FMF_FAMSHR:
                    self.any_device_being_updated_flag = False
                    self.iosapp_location_update_secs[devicename] = 0

                    event_msg = ("iOS update was not completed, "
                        f"will retry with {self.trk_method_short_name}")
                    self._save_event_halog_debug(devicename, event_msg)

                    return ICLOUD_UPDATE

                #Note: Final prep and update device attributes via
                #device_tracker.see. The gps location, battery, and
                #gps accuracy are not part of the attrs variable and are
                #reformatted into device attributes by 'See'. The gps
                #location goes to 'See' as a "(latitude, longitude)" pair.
                #'See' converts them to ATTR_LATITUDE and ATTR_LONGITUDE
                #and discards the 'gps' item.

                log_msg = (f"►LOCATION ATTRIBUTES, State-{self.state_last_poll.get(devicename)}, "
                           f"Attrs-{attrs}")
                self.log_debug_msg(devicename, log_msg)

                #If location is empty or trying to set to the Stationary Base Zone Location,
                #discard the update and try again in 15-sec
                if self._update_last_latitude_longitude(devicename, latitude, longitude, 1920) == False:
                    self.any_device_being_updated_flag = False
                    return ICLOUD_UPDATE

                self.count_update_iosapp[devicename] += 1
                self.last_battery[devicename]      = battery
                self.last_gps_accuracy[devicename] = gps_accuracy
                self.last_located_time[devicename] = self._time_to_12hrtime(timestamp)

                if altitude is None:
                    altitude = 0

                attrs[ATTR_LAST_LOCATED]   = self._time_to_12hrtime(timestamp)
                attrs[ATTR_DEVICE_STATUS]  = device_status
                attrs[ATTR_LOW_POWER_MODE] = low_power_mode
                attrs[ATTR_BATTERY]        = battery
                attrs[ATTR_BATTERY_STATUS] = battery_status
                attrs[ATTR_ALTITUDE]       = round(altitude, 2)
                attrs[ATTR_VERT_ACCURACY] = vertical_accuracy
                attrs[ATTR_POLL_COUNT]     = self._format_poll_count(devicename)

            except Exception as err:
                _LOGGER.exception(err)
                #attrs = self._internal_error_msg(fct_name, err, 'SetAttrsDev')

            try:
                kwargs = self._setup_base_kwargs(
                    devicename,
                    latitude,
                    longitude,
                    battery,
                    gps_accuracy)

                self._update_device_attributes(devicename, kwargs, attrs, 'Final Update')
                self._update_device_sensors(devicename, kwargs)
                self._update_device_sensors(devicename, attrs)

                self.seen_this_device_flag[devicename]     = True
                self.device_being_updated_flag[devicename] = False

            except Exception as err:
                _LOGGER.exception(err)
                log_msg = (f"{self._format_fname_devtype(devicename)} "
                           f"Error Updating Device, {err}")
                self.log_error_msg(log_msg)
                return_code = ICLOUD_UPDATE

            try:
                event_msg = (f"IOS App v{self.iosapp_version.get(devicename)} update complete")
                self._save_event(devicename, event_msg)

                self._log_start_finish_update_banner('▲▲▲', devicename,
                            iosapp_version_text, update_reason)

                entity_id = self.device_tracker_entity.get(devicename)
                dev_attrs = self._get_device_attributes(entity_id)
                #self._trace_device_attributes(devicename, 'after Final', fct_name, dev_attrs)

                return_code = IOSAPP_UPDATE

            except KeyError as err:
                self._internal_error_msg(fct_name, err, 'iosUpdateMsg')
                return_code = ICLOUD_UPDATE

        except Exception as err:
            _LOGGER.exception(err)
            self._internal_error_msg(fct_name, err, 'OverallUpdate')
            self.device_being_updated_flag[devicename] = False
            return_code = ICLOUD_UPDATE

        self.any_device_being_updated_flag = False
        self.iosapp_location_update_secs[devicename] = 0
        return return_code

#########################################################
#
#   This function is called every 10 seconds. Cycle through all
#   of the devices to see if any of the ones being tracked will
#   be updated on the 15-sec polling loop in 5-secs. If so, request a
#   location update now so it might be current when the device
#   is updated.
#
#########################################################
    def _polling_loop_10_sec_fmf_loc_prefetch(self, now):

        try:
            if self.next_update_secs is None:
                return
            elif self.TRK_METHOD_IOSAPP:
                return

            for devicename_zone in self.next_update_secs:
                time_till_update = self.next_update_secs.get(devicename_zone) - \
                        self.this_update_secs
                if time_till_update <= 10:
                    devicename    = devicename_zone.split(':')[0]
                    location_data = self.location_data.get(devicename)
                    age           = location_data[ATTR_AGE]

                    if age > 15:
                        if self.TRK_METHOD_FMF_FAMSHR:
                            self._refresh_pyicloud_devices_location_data(age, devicename)
                        #else:
                        #    self._request_iosapp_location_update(devicename)
                    break

        except Exception as err:
            _LOGGER.exception(err)

        return

#########################################################
#
#   This function is called every 15 seconds. Cycle through all
#   of the iCloud devices to see if any of the ones being tracked need
#   to be updated. If so, we might as well update the information for
#   all of the devices being tracked since PyiCloud gets data for
#   every device in the account.
#
#########################################################
    def _polling_loop_15_sec_icloud(self, now):
        """Called every 15-sec to check iCloud update"""

        if self.any_device_being_updated_flag:
            return
        elif self.TRK_METHOD_IOSAPP:
            return

        fct_name = "_polling_loop_15_sec_icloud"

        self.this_update_secs = self._time_now_secs()
        this_update_time = dt_util.now().strftime(self.um_time_strfmt)

        try:
            for devicename in self.tracked_devices:
                update_reason = "Location Update"
                devicename_zone = self._format_devicename_zone(devicename, HOME)

                if (self.tracking_device_flag.get(devicename) is False or
                   self.next_update_time.get(devicename_zone) == PAUSED):
                    continue

                self.iosapp_update_flag[devicename] = False
                update_method = False

                # If the state changed since last poll, force an update
                # This can be done via device_tracker.see service call
                # with a different location_name in an automation or
                # from entering a zone via the IOS App.
                entity_id     = self.device_tracker_entity.get(devicename)
                state = self._get_state(entity_id)

                if state != self.state_last_poll.get(devicename):
                    update_method = True

                    update_reason = "State Change"
                    event_msg     = (f"State Change detected for {devicename} > "
                                     f"{self.state_last_poll.get(devicename)} to "
                                     f"{state}")
                    self._save_event_halog_info('*', event_msg)

                if update_method:
                    if 'nearzone' in state:
                        state = 'near_zone'

                    self.state_this_poll[devicename]       = state
                    self.next_update_secs[devicename_zone] = 0

                    attrs  = {}
                    attrs[ATTR_INTERVAL]           = '0 sec'
                    attrs[ATTR_NEXT_UPDATE_TIME]   = HHMMSS_ZERO
                    self._update_device_sensors(devicename, attrs)

                #This flag will be 'true' if the last update for this device
                #was not completed. Do another update now.
                if (self.device_being_updated_flag.get(devicename) and
                    self.device_being_updated_retry_cnt.get(devicename) > 4):
                    self.device_being_updated_flag[devicename] = False
                    self.device_being_updated_retry_cnt[devicename] = 0
                    self.log_debug_msgs_trace_flag = False

                    log_msg = (f"{self._format_fname_devtype(devicename)} Cancelled update retry")
                    self.log_info_msg(log_msg)

                if self._check_in_zone_and_before_next_update(devicename):
                    continue

                elif self.device_being_updated_flag.get(devicename):
                    update_method = True
                    self.log_debug_msgs_trace_flag = True
                    self.device_being_updated_retry_cnt[devicename] += 1

                    update_reason = "Retry Last Update"
                    event_msg     = (f"{trk_method_short_name} update not completed, retrying")
                    self._save_event_halog_info(devicename, event_msg)

                elif self.next_update_secs.get(devicename_zone) == 0:
                    update_method       = True
                    self.trigger[devicename] = 'StateChange/Resume'
                    self.log_debug_msgs_trace_flag = False
                    update_reason = "State Change/Resume"
                    event_msg     = "State Change or Resume Polling Requested"
                    self._save_event(devicename, event_msg)

                else:
                    update_via_other_devicename = self._check_next_update_time_reached()
                    if update_via_other_devicename is not None:
                        self.log_debug_msgs_trace_flag = False
                        update_method       = True
                        self.trigger[devicename] = 'NextUpdateTime'

                        update_reason = "Next Update Time"
                        event_msg     = (f"NextUpdateTime reached > {update_via_other_devicename}")
                        self._save_event(devicename, event_msg)

                if update_method:
                    self._wait_if_update_in_process()
                    self.update_in_process_flag = True

                    if self.icloud_authenticate_account():
                        self.info_notification = (f"THE ICLOUD 2SA CODE IS NEEDED TO VERIFY "
                                                    f"THE ACCOUNT FOR {self.username}")
                        for devicename in self.tracked_devices:
                            self._display_info_status_msg(devicename, self.info_notification)

                            log_msg = (f"iCloud3 Error > The iCloud 2fa code for account "
                                    f"{self.username} needs to be verified. Use the HA "
                                    f"Notifications area on the HA Sidebar at the bottom "
                                    f"the HA main screen.")
                            self._save_event_halog_error(devicename, log_msg)
                        return

                    self._update_device_icloud(update_reason)

                self.update_in_process_flag = False

        except Exception as err:       #ValueError:
            _LOGGER.exception(err)

            log_msg = (f"►iCloud/FmF API Error, Error-{ValueError}")
            self.log_error_msg(log_msg)
            self.api.authenticate()           #Reset iCloud
            self.authenticated_time = time.time()
            self._update_device_icloud('iCloud/FmF Reauth')    #Retry update devices

            self.update_in_process_flag = False
            self.log_debug_msgs_trace_flag = False


#########################################################
#
#   Cycle through all iCloud devices and update the information for the devices
#   being tracked
#     ●►●◄►●▬▲▼◀►►●◀ oPhone=►▶
#########################################################
    def _update_device_icloud(self, update_reason='Check iCloud',
            arg_devicename=None):
        """
        Request device information from iCloud (if needed) and update
        device_tracker information.
        """

        if self.TRK_METHOD_IOSAPP:
            return
        elif self.start_icloud3_inprocess_flag:
            return
        elif self.any_device_being_updated_flag:
            return
        fct_name = "_update_device_icloud"

        self.any_device_being_updated_flag = True
        self.base_zone                     = HOME

        try:
            for devicename in self.tracked_devices:
                zone    = self.zone_current.get(devicename)
                devicename_zone = self._format_devicename_zone(devicename)

                if arg_devicename and devicename != arg_devicename:
                    continue
                elif self.next_update_time.get(devicename_zone) == PAUSED:
                    continue


                #If the device is in a zone, and was in the same zone on the
                #last poll of another device on the account and this device
                #update time has not been reached, do not update device
                #information. Do this in case this device currently has bad gps
                #and really doesn't need to be polled at this time anyway.
                #If the iOS App triggered the update and it was not done by the
                #iosapp_update routine, do one now anyway.
                if (self._check_in_zone_and_before_next_update(devicename) and
                        arg_devicename == None):
                    continue

                event_msg = (f"{self.trk_method_short_name} update started "
                             f"({update_reason.split('@')[0]})")
                self._save_event_halog_info(devicename, event_msg)

                self._log_start_finish_update_banner('▼▼▼', devicename,
                            self.trk_method_short_name, update_reason)

                self.update_timer[devicename] = time.time()
                self.iosapp_location_update_secs[devicename] = 0
                do_not_update_flag = False
                location_time      = 0

                #Updating device info. Get data from FmF or FamShr and update
                if self.TRK_METHOD_FMF:
                    valid_data_flag = self._get_fmf_data(devicename)

                elif self.TRK_METHOD_FAMSHR:
                    valid_data_flag = self._get_famshr_data(devicename)

                #An error ocurred accessing the iCloud acount. This can be a
                #Authentication error or an error retrieving the loction data
                #if dev_data[0] is False:
                if valid_data_flag == ICLOUD_LOCATION_DATA_ERROR:
                    self.icloud_acct_auth_error_cnt += 1
                    self._determine_interval_retry_after_error(
                        devicename,
                        self.icloud_acct_auth_error_cnt,
                        "iCloud Offline (Authentication or Location Error)")

                    if (self.interval_seconds.get(devicename) != 15 and
                        self.icloud_acct_auth_error_cnt > 2):
                        log_msg = ("iCloud3 Error > An error occurred accessing "
                            f"the iCloud account {self.username} for {devicename}. This can be an account "
                            "authentication issue or no location data is "
                            "available. Retrying at next update time. "
                            "Retry #{self.icloud_acct_auth_error_cnt}")
                        self._save_event_halog_error("*", log_msg)

                    if self.icloud_acct_auth_error_cnt > 20:
                        self._setup_tracking_method(IOSAPP)
                        log_msg = ("iCloud3 Error > More than 20 iCloud Authentication "
                            "errors. Resetting to use tracking_method <iosapp>. "
                            "Restart iCloud3 at a later time to see if iCloud "
                            "Loction Services is available.")
                        self._save_event_halog_error("*", log_msg)

                    break
                else:
                    self.icloud_acct_auth_error_cnt = 0

                #icloud data overrules device data which may be stale
                location_data = self.location_data.get(devicename)
                latitude      = location_data[ATTR_LATITUDE]
                longitude     = location_data[ATTR_LONGITUDE]

                #Discard if no location coordinates
                if latitude == 0 or longitude == 0:
                    info_msg = (f"No Location Coordinates, ({latitude}, {longitude})")

                    self._determine_interval_retry_after_error(
                        devicename,
                        self.old_loc_poor_gps_cnt.get(devicename),
                        info_msg)
                    do_not_update_flag = True

                else:
                    timestamp           = location_data[ATTR_TIMESTAMP]
                    location_isold_attr = location_data[ATTR_ISOLD]
                    location_time_secs  = location_data[ATTR_TIMESTAMP]
                    location_time       = location_data[ATTR_TIMESTAMP_TIME]
                    battery             = location_data[ATTR_BATTERY_LEVEL]
                    battery_status      = location_data[ATTR_BATTERY_STATUS]
                    device_status       = location_data[ATTR_DEVICE_STATUS]
                    low_power_mode      = location_data[ATTR_LOW_POWER_MODE]
                    altitude            = location_data[ATTR_ALTITUDE]
                    gps_accuracy        = location_data[ATTR_GPS_ACCURACY]
                    vertical_accuracy   = location_data[ATTR_VERT_ACCURACY]

                    location_age        = self._secs_since(location_data.get(ATTR_TIMESTAMP))
                    location_data[ATTR_AGE] = location_age
                    location_isold_flag = self._check_old_loc_poor_gps(
                                                    devicename,
                                                    location_time_secs,
                                                    gps_accuracy)

                    self.last_located_secs[devicename] = location_time_secs
                    #location_age = self._secs_since(location_time_secs)

                #Check to see if currently in a zone. If so, check the zone distance.
                #If new location is outside of the zone and inside radius*4, discard
                #by treating it as poor GPS
                if self._is_inzoneZ(zone):
                    outside_no_exit_trigger_flag, info_msg = \
                        self._check_outside_zone_no_exit(devicename, zone, latitude, longitude)
                    if outside_no_exit_trigger_flag:
                        self.poor_gps_accuracy_flag[devicename] = True
                else:
                    outside_no_exit_trigger_flag = False
                    info_msg= ''

                #If not authorized or no data, don't check old or accuracy errors
                if self.icloud_acct_auth_error_cnt > 0:
                    pass

                #If initializing, nothing is set yet
                elif self.state_this_poll.get(devicename) == NOT_SET:
                    pass

                #If no location data
                elif do_not_update_flag:
                    pass

                #Outside zone, no exit trigger check
                elif outside_no_exit_trigger_flag:
                    self.poor_gps_accuracy_flag[devicename] = True
                    self.old_loc_poor_gps_cnt[devicename] += 1
                    do_not_update_flag = True
                    self._determine_interval_retry_after_error(
                        devicename,
                        self.old_loc_poor_gps_cnt.get(devicename),
                        info_msg)

                #Discard if poor gps
                elif self.poor_gps_accuracy_flag.get(devicename):
                    info_msg = (f"Poor GPS Accuracy (#{self.old_loc_poor_gps_cnt.get(devicename)})")

                    do_not_update_flag = True
                    self._determine_interval_retry_after_error(
                        devicename,
                        self.old_loc_poor_gps_cnt.get(devicename),
                        info_msg)

                #Discard if location is too old
                elif location_isold_flag:
                    info_msg = (f"Old Location (#{self.old_loc_poor_gps_cnt.get(devicename)})")

                    do_not_update_flag = True
                    self._determine_interval_retry_after_error(
                        devicename,
                        self.old_loc_poor_gps_cnt.get(devicename),
                        info_msg)

                #discard if outside home zone and less than zone_radius+self.gps_accuracy_threshold due to gps errors
                dist_from_home_m = self._calc_distance_m(latitude, longitude,
                                            self.zone_home_lat, self.zone_home_long)

                if do_not_update_flag:
                    event_msg = (f"Discarding > {info_msg} > GPS-{format_gps(latitude, longitude)}, "
                                 f"GPSAccuracy-{gps_accuracy} m, Located-{location_time} "
                                 f"({self._secs_to_time_str(location_age)} ago), "
                                 f"OldLocThreshold-{self._secs_to_time_str(self.old_location_secs.get(devicename))}")
                    self._save_event(devicename, event_msg)

                    self._log_start_finish_update_banner('▲▲▲', devicename,
                            self.trk_method_short_name, update_reason)
                    continue

                #--------------------------------------------------------
                try:
                    if self.device_being_updated_flag.get(devicename):
                        info_msg  = "Retrying > Last update not completed"
                        event_msg = info_msg
                    else:
                        info_msg = "Updating"
                        event_msg = (f"Updating Device > GPS-{format_gps(latitude, longitude)}, "
                            f"GPSAccuracy-{gps_accuracy} m, "
                            f"Located-{location_time} ({self._secs_to_time_str(location_age)} ago)")
                    info_msg = f"● {info_msg} {self.fname.get(devicename)} ●"
                    self._display_info_status_msg(devicename, info_msg)
                    self._save_event(devicename, event_msg)

                    #set device being updated flag. This is checked in the
                    #'_polling_loop_15_sec_icloud' loop to make sure the last update
                    #completed successfully (Waze has a compile error bug that will
                    #kill update and everything will sit there until the next poll.
                    #if this is still set in '_polling_loop_15_sec_icloud', repoll
                    #immediately!!!
                    self.device_being_updated_flag[devicename] = True

                except Exception as err:
                    attrs = self._internal_error_msg(fct_name, err, 'UpdateAttrs1')

                try:
                    for zone in self.track_from_zone.get(devicename):
                        self._set_base_zone_name_lat_long_radius(zone)

                        self._log_start_finish_update_banner('▼-▼', devicename,
                            self.trk_method_short_name, zone)

                        attrs = self._determine_interval(
                            devicename,
                            latitude,
                            longitude,
                            battery,
                            gps_accuracy,
                            location_isold_flag,
                            location_time_secs,
                            location_time,
                            "icld")
                        if attrs != {}:
                            self._update_device_sensors(devicename, attrs)

                        self._log_start_finish_update_banner('▲-▲', devicename,
                            self.trk_method_short_name,zone)

                except Exception as err:
                    attrs = self._internal_error_msg(fct_name, err, 'DetInterval')
                    continue

                try:
                    #Note: Final prep and update device attributes via
                    #device_tracker.see. The gps location, battery, and
                    #gps accuracy are not part of the attrs variable and are
                    #reformatted into device attributes by 'See'. The gps
                    #location goes to 'See' as a "(latitude, longitude)" pair.
                    #'See' converts them to ATTR_LATITUDE and ATTR_LONGITUDE
                    #and discards the 'gps' item.
                    log_msg = (f"►LOCATION ATTRIBUTES, State-{self.state_last_poll.get(devicename)}, "
                                f"Attrs-{attrs}")
                    self.log_debug_msg(devicename, log_msg)

                    self.count_update_icloud[devicename] += 1
                    if not location_isold_flag:
                        self._update_last_latitude_longitude(devicename, latitude, longitude, 2277)

                    if altitude is None:
                        altitude = -2

                    attrs[ATTR_DEVICE_STATUS]  = device_status
                    attrs[ATTR_LOW_POWER_MODE] = low_power_mode
                    attrs[ATTR_BATTERY]        = battery
                    attrs[ATTR_BATTERY_STATUS] = battery_status
                    attrs[ATTR_ALTITUDE]       = round(altitude, 2)
                    attrs[ATTR_VERT_ACCURACY]  = vertical_accuracy
                    attrs[ATTR_POLL_COUNT]     = self._format_poll_count(devicename)
                    attrs[ATTR_AUTHENTICATED]  = self._secs_to_timestamp(self.authenticated_time)

                except Exception as err:
                    attrs = self._internal_error_msg(fct_name, err, 'SetAttrs')

                try:
                    kwargs = self._setup_base_kwargs(devicename,
                        latitude, longitude, battery, gps_accuracy)

                    self._update_device_sensors(devicename, kwargs)
                    self._update_device_sensors(devicename, attrs)
                    self._update_device_attributes(devicename, kwargs,
                            attrs, 'Final Update')

                    self.seen_this_device_flag[devicename]     = True
                    self.device_being_updated_flag[devicename] = False

                except Exception as err:
                    log_msg = (f"{self._format_fname_devtype(devicename)} Error Updating Device, {err}")
                    self.log_error_msg(log_msg)

                    _LOGGER.exception(err)

                try:
                    event_msg = (f"{self.trk_method_short_name} update completed")
                    self._save_event(devicename, event_msg)

                    self._log_start_finish_update_banner('▲▲▲', devicename,
                            self.trk_method_short_name, update_reason)

                except KeyError as err:
                    self._internal_error_msg(fct_name, err, 'icloudUpdateMsg')

        except Exception as err:
            _LOGGER.exception(err)
            self._internal_error_msg(fct_name, err, 'OverallUpdate')
            self.device_being_updated_flag[devicename] = False

        self.any_device_being_updated_flag = False

#########################################################
#
#   Get iCloud device & location info when using the
#   FmF (Find-my-Friends / Find Me) tracking method.
#
#########################################################
    def _get_fmf_data(self, devicename):
        '''
        Get the location data from Find My Friends.

        location_data-{
            'locationStatus': None,
            'location': {
                'isInaccurate': False,
                'altitude': 0.0,
                'address': {'formattedAddressLines': ['123 Main St',
                    'Your City, NY', 'United States'],
                    'country': 'United States',
                    'streetName': 'Main St,
                    'streetAddress': '123 Main St',
                    'countryCode': 'US',
                    'locality': 'Your City',
                    'stateCode': 'NY',
                    'administrativeArea': 'New York'},
                'locSource': None,
                'latitude': 12.34567890,
                'floorLevel': 0,
                'horizontalAccuracy': 65.0,
                'labels': [{'id': '79f8e34c-d577-46b4-a6d43a7b891eca843',
                    'latitude': 12.34567890,
                    'longitude': -45.67890123,
                    'info': None,
                    'label': '_$!<home>!$_',
                    'type': 'friend'}],
                'tempLangForAddrAndPremises': None,
                'verticalAccuracy': 0.0,
                'batteryStatus': None,
                'locationId': 'a6b0ee1d-be34-578a-0d45-5432c5753d3f',
                'locationTimestamp': 0,
                'longitude': -45.67890123,
                'timestamp': 1562512615222},
            'id': 'NDM0NTU2NzE3',
            'status': None}
        '''

        fct_name = "_get_fmf_data"
        from .pyicloud_ic3 import PyiCloudNoDevicesException

        log_msg = (f"= = = Prep Data From FmF = = = (Now-{self.this_update_secs})")
        self.log_debug_msg(devicename, log_msg)

        try:
            location_data = self.location_data.get(devicename)

            log_msg = (f"Current Location Data-{location_data})")
            self.log_debug_msg(devicename, log_msg)

            age       = location_data[ATTR_AGE]

            if age > self.old_location_secs.get(devicename):
                if self._refresh_pyicloud_devices_location_data(age, devicename):
                    location_data = self.location_data.get(devicename)
                else:
                    if self.icloud_acct_auth_error_cnt > 3:
                        self.log_error_msg(f"iCloud3 Error > No Location Data "
                                           f"Returned for {devicename}")
                    return ICLOUD_LOCATION_DATA_ERROR
            return True

        except Exception as err:
            _LOGGER.exception(err)
            self.log_error_msg("General iCloud Location Data Error")
            return ICLOUD_LOCATION_DATA_ERROR

#########################################################
#
#   Get iCloud device & location info when using the
#   FamShr (Family Sharing) tracking method.
#
#########################################################
    def _get_famshr_data(self, devicename):
        '''
        Extract the data needed to determine location, direction, interval,
        etc. from the iCloud data set.

        Sample data set is:
            {'isOld': False, 'isInaccurate': False, 'altitude': 0.0, 'positionType': 'Wifi',
            'latitude': 27.72690098883266, 'floorLevel': 0, 'horizontalAccuracy': 65.0,
            'locationType': '', 'timeStamp': 1587306847548, 'locationFinished': True,
            'verticalAccuracy': 0.0, 'longitude': -80.3905776599289}
        '''

        fct_name = "_get_famshr_data"

        log_msg = (f"= = = Prep Data From FamShr = = = (Now-{self.this_update_secs})")
        self.log_debug_msg(devicename, log_msg)

        try:
            location_data = self.location_data.get(devicename)

            log_msg = (f"Current Location Data-{location_data})")
            self.log_debug_msg(devicename, log_msg)

            age = location_data[ATTR_AGE]

            if age > self.old_location_secs.get(devicename):
                if self._refresh_pyicloud_devices_location_data(age, devicename):
                    location_data = self.location_data.get(devicename)
                else:
                    if self.icloud_acct_auth_error_cnt > 3:
                        self.log_error_msg(f"iCloud3 Error > No Location Data "
                                           f"Returned for {devicename}")
                    return ICLOUD_LOCATION_DATA_ERROR
            return True

        except Exception as err:
            _LOGGER.exception(err)
            self.log_error_msg("General iCloud FamShr Location Data Error")
            return ICLOUD_LOCATION_DATA_ERROR

#----------------------------------------------------------------------------
    def _refresh_pyicloud_devices_location_data(self, age, arg_devicename):
        '''
        Authenticate pyicloud & refresh device & location data. This calls the
        function to update 'self.location_data' for each device being tracked.

        Return: True if device data was updated successfully
                False if api error or no device data returned
        '''

        try:
            event_msg=(f"Locating Device > Last Updated")
            if age == HIGH_INTEGER:
                event_msg += (f": Never (Initial Locate)")
            else:
                event_msg += (f" {self.location_data.get(arg_devicename)[ATTR_TIMESTAMP_TIME]} "
                              f"({self._secs_to_time_str(age)} ago)")
            self._save_event_halog_info(arg_devicename, event_msg)

            exit_get_data_loop = False
            authenticated_pyicloud_flag = False
            self.count_pyicloud_location_update += 1
            pyicloud_start_call_time = time.time()

            while exit_get_data_loop == False:
                try:
                    if self.api == None:
                        return False

                    if self.TRK_METHOD_FMF:
                        self.api.friends.refresh_client()
                        devices = self.api.friends
                        locations = devices.locations

                        for location in locations:
                            if ATTR_LOCATION in location:
                                contact_id = location['id']
                                devicename = self.fmf_id[contact_id]

                                self._update_location_data(devicename, location)

                    elif self.TRK_METHOD_FAMSHR:
                        api_devices = {}
                        api_devices = self.api.devices
                        api_device_data = api_devices.response["content"]

                        for device in api_device_data:
                            if device:
                                device_data_name = device[ATTR_NAME]
                                if device_data_name in self.api_device_devicename:
                                    devicename = self.api_device_devicename.get(device_data_name)
                                    if devicename in self.tracked_devices:
                                        self._update_location_data(devicename, device)

                except PyiCloudAPIResponseException as err:
                    if authenticated_pyicloud_flag:
                        return False

                    authenticated_pyicloud_flag = True
                    self._authenticate_pyicloud()

                except Exception as err:
                    _LOGGER.exception(err)

                else:
                    exit_get_data_loop = True

            update_took_time = time.time() - pyicloud_start_call_time
            self.time_pyicloud_calls += update_took_time

            return True

        except Exception as err:
            _LOGGER.exception(err)

        return False

#----------------------------------------------------------------------------
    def _update_location_data(self, devicename, device_data):
        '''
        Extract the location_data dictionary table from the device
        data returned from pyicloud for the devicename device. This data is used to
        determine the update interval, accuracy, location, etc.
        '''
        try:
            if device_data == None:
                return False
            elif ATTR_LOCATION not in device_data:
                return False
            elif device_data[ATTR_LOCATION] == {}:
                return

            self.log_level_debug_rawdata("update_location_data (device_data)", device_data)

            timestamp_field = ATTR_TIMESTAMP if self.TRK_METHOD_FMF else ATTR_ICLOUD_TIMESTAMP
            timestamp       = device_data[ATTR_LOCATION][timestamp_field] / 1000

            if timestamp == self.location_data.get(devicename)[ATTR_TIMESTAMP]:
                age = self.location_data.get(devicename)[ATTR_AGE]
                debug_msg = (f"Device Not Updated > Will Refresh, Located-{self._secs_to_time(timestamp)} "
                             f"({self._secs_to_time_str(age)} ago)")
                self.log_debug_msg(devicename, debug_msg)
                return

            location_data                      = {}
            location_data[ATTR_NAME]           = device_data.get(ATTR_NAME, "")
            location_data[ATTR_DEVICE_CLASS]   = device_data.get(ATTR_ICLOUD_DEVICE_CLASS, "")
            location_data[ATTR_BATTERY_LEVEL]  = int(device_data.get(ATTR_ICLOUD_BATTERY_LEVEL, 0) * 100)
            location_data[ATTR_BATTERY_STATUS] = device_data.get(ATTR_ICLOUD_BATTERY_STATUS, "")

            device_status_code                 = device_data.get(ATTR_ICLOUD_DEVICE_STATUS, 0)
            location_data[ATTR_DEVICE_STATUS]  = DEVICE_STATUS_CODES.get(device_status_code, "")
            location_data[ATTR_LOW_POWER_MODE] = device_data.get(ATTR_ICLOUD_LOW_POWER_MODE, "")

            location                           = device_data[ATTR_LOCATION]
            location_data[ATTR_TIMESTAMP]      = timestamp
            location_data[ATTR_TIMESTAMP_TIME] = self._secs_to_time(timestamp)
            location_data[ATTR_AGE]            = self._secs_since(timestamp)
            location_data[ATTR_LATITUDE]       = location.get(ATTR_LATITUDE, 0)
            location_data[ATTR_LONGITUDE]      = location.get(ATTR_LONGITUDE, 0)
            location_data[ATTR_ALTITUDE]       = round(location.get(ATTR_ALTITUDE, 0), 1)
            location_data[ATTR_ISOLD]          = location.get(ATTR_ISOLD, False)
            location_data[ATTR_GPS_ACCURACY]   = round(location.get(ATTR_ICLOUD_HORIZONTAL_ACCURACY, 0), 0)
            location_data[ATTR_VERT_ACCURACY] = round(location.get(ATTR_ICLOUD_VERTICAL_ACCURACY, 0), 0)

            self.location_data[devicename] = location_data

            debug_msg = (f"Device Updated > Located-{location_data[ATTR_TIMESTAMP_TIME]} "
                         f"({self._secs_to_time_str(location_data[ATTR_AGE])} ago)")
            self.log_debug_msg(devicename, debug_msg)
            self.log_debug_msg(devicename, location_data)

            return True

        except Exception as err:
            _LOGGER.exception(err)

        return False

#########################################################
#
#   iCloud is disabled so trigger the iosapp to send a
#   Background Fetch location transaction
#
#########################################################
    def _request_iosapp_location_update(self, devicename):
        #service: notify.ios_<your_device_id_here>
        #  data:
        #    message: "request_location_update"


        if (self.count_request_iosapp_locate.get(devicename) > self.max_iosapp_locate_cnt):
            return

        request_msg_suffix = ''

        try:
            #if time > 0, then waiting for requested update to occur, update age
            if self.iosapp_location_update_secs.get(devicename) > 0:
                age = self._secs_since(self.iosapp_location_update_secs.get(devicename))
                request_msg_suffix = (f" {self._secs_to_time_str(age)} ago")

            else:
                self.iosapp_location_update_secs[devicename] = self.this_update_secs
                self.count_request_iosapp_locate[devicename] += 1

                entity_id = f"{self.notify_iosapp_entity.get(devicename)}"
                service_data = {"message": "request_location_update"}
                #self.hass.services.call("notify", entity_id, service_data)

                self.hass.async_create_task(
                    self.hass.services.async_call('notify',  entity_id, service_data))
                event_msg = (f"Requested iOS App Location (#{self.count_request_iosapp_locate.get(devicename)})")
                self._save_event(devicename, event_msg)

                log_msg = (f"{self._format_fname_devtype(devicename)} {event_msg}")
                self.log_debug_msg(devicename, log_msg)

            attrs = {}
            attrs[ATTR_POLL_COUNT] = self._format_poll_count(devicename)
            attrs[ATTR_INFO] = (f"● Requested iOS App Location "
                                f"(#{self.count_request_iosapp_locate.get(devicename)})"
                                f"{request_msg_suffix} ●")
            self._update_device_sensors(devicename, attrs)

        except Exception as err:
            _LOGGER.exception(err)
            error_msg = (f"iCloud3 Error > An error was encountered processing "
                         f"device `location`request - {err}")
            self._save_event_halog_error(devicename, error_msg)


#########################################################
#
#   Calculate polling interval based on zone, distance from home and
#   battery level. Setup triggers for next poll
#
#########################################################
    def _determine_interval(self, devicename, latitude, longitude,
                    battery, gps_accuracy,
                    location_isold_flag, location_time_secs, location_time,
                    ios_icld = ''):
        """Calculate new interval. Return location based attributes"""

        fct_name = "_determine_interval"

        base_zone_home_flag  = (self.base_zone == HOME)
        devicename_zone = self._format_devicename_zone(devicename)

        try:
            #self.base_zone_name   = self.zone_fname.get(self.base_zone)
            #self.base_zone_lat    = self.zone_lat.get(self.base_zone)
            #self.base_zone_long   = self.zone_long.get(self.base_zone)
            #self.base_zone_radius_km = float(self.zone_radius_km.get(self.base_zone))

            #self._set_base_zone_name_lat_long_radius(self.base_zone)

            location_data = self._get_distance_data(
                devicename,
                latitude,
                longitude,
                gps_accuracy,
                location_isold_flag)

            log_msg = (f"Location_data-{location_data}")
            self.log_debug_interval_msg(devicename, log_msg)

            #Abort and Retry if Internal Error
            if (location_data[0] == 'ERROR'):
                return location_data[1]     #(attrs)

            zone                 = location_data[0]
            dir_of_travel                = location_data[1]
            dist_from_zone_km            = location_data[2]
            dist_from_zone_moved_km      = location_data[3]
            dist_last_poll_moved_km      = location_data[4]
            waze_dist_from_zone_km       = location_data[5]
            calc_dist_from_zone_km       = location_data[6]
            waze_dist_from_zone_moved_km = location_data[7]
            calc_dist_from_zone_moved_km = location_data[8]
            waze_dist_last_poll_moved_km = location_data[9]
            calc_dist_last_poll_moved_km = location_data[10]
            waze_time_from_zone          = location_data[11]
            last_dist_from_zone_km       = location_data[12]
            last_dir_of_travel           = location_data[13]
            dir_of_trav_msg              = location_data[14]
            timestamp                    = location_data[15]


        except Exception as err:
            attrs_msg = self._internal_error_msg(fct_name, err, 'SetLocation')
            return attrs_msg

        try:
            log_msg = (f"►DETERMINE INTERVAL Entered, "
                          "location_data-{location_data}")
            self.log_debug_interval_msg(devicename, log_msg)

    #       The following checks the distance from home and assigns a
    #       polling interval in minutes.  It assumes a varying speed and
    #       is generally set so it will poll one or twice for each distance
    #       group. When it gets real close to home, it switches to once
    #       each 15 seconds so the distance from home will be calculated
    #       more often and can then be used for triggering automations
    #       when you are real close to home. When home is reached,
    #       the distance will be 0.

            waze_time_msg = ""
            calc_interval = round(self._km_to_mi(dist_from_zone_km) / 1.5) * 60
            if self.waze_status == WAZE_USED:
                waze_interval = \
                    round(waze_time_from_zone * 60 * self.travel_time_factor , 0)
            else:
                waze_interval = 0
            interval = 15
            interval_multiplier = 1

            inzone_flag          = (self._is_inzoneZ(zone))
            not_inzone_flag      = (self._isnot_inzoneZ(zone))
            was_inzone_flag      = (self._was_inzone(devicename))
            wasnot_inzone_flag   = (self._wasnot_inzone(devicename))
            inzone_home_flag     = (zone == self.base_zone)     #HOME)
            was_inzone_home_flag = \
                (self.state_last_poll.get(devicename) == self.base_zone) #HOME)
            near_zone_flag       = (zone == 'near_zone')

            log_msg =  (f"Zone-{zone} ,IZ-{inzone_flag}, NIZ-{not_inzone_flag}, "
                        f"WIZ-{was_inzone_flag}, WNIZ-{wasnot_inzone_flag}, "
                        f"IZH-{inzone_home_flag}, WIZH-{was_inzone_home_flag}, "
                        f"NZ-{near_zone_flag}")
            self.log_debug_interval_msg(devicename, log_msg)

            log_method  = ''
            log_msg     = ''
            log_method_im  = ''
            old_location_secs_msg = ''

        except Exception as err:
            attrs_msg = self._internal_error_msg(fct_name, err, 'SetupZone')
            return attrs_msg

        try:
            #Note: If state is 'near_zone', it is reset to NOT_HOME when
            #updating the device_tracker state so it will not trigger a state chng
            if self.state_change_flag.get(devicename):
                if inzone_flag:
                    #Reset got zone exit trigger since now in a zone for next
                    #exit distance check
                    self.got_exit_trigger_flag[devicename] = False

                    if (STATIONARY in zone):
                        interval = self.stat_zone_inzone_interval
                        log_method = "1sz-Stationary"
                        log_msg    = f"Zone-{zone}"

                    #inzone & old location
                    elif location_isold_flag:
                        interval = self._get_interval_for_error_retry_cnt(
                                        self.old_loc_poor_gps_cnt.get(devicename))
                        log_method = '1iz-OldLoc'

                    else:
                        interval = self.inzone_interval
                        log_method="1ez-EnterZone"

                #entered 'near_zone' zone if close to HOME and last is NOT_HOME
                elif (near_zone_flag and wasnot_inzone_flag and
                        calc_dist_from_zone_km < 2):
                    interval = 15
                    dir_of_travel = 'NearZone'
                    log_method="1nz-EnterHomeNearZone"

                #entered 'near_zone' zone if close to HOME and last is NOT_HOME
                elif (near_zone_flag and was_inzone_flag and
                        calc_dist_from_zone_km < 2):
                    interval = 15
                    dir_of_travel = 'NearZone'
                    log_method="1nhz-EnterNearHomeZone"

                #exited HOME zone
                elif (not_inzone_flag and was_inzone_home_flag):
                    interval = 240
                    dir_of_travel = AWAY_FROM
                    log_method="1ehz-ExitHomeZone"

                #exited 'other' zone
                elif (not_inzone_flag and was_inzone_flag):
                    interval = 120
                    dir_of_travel = 'left_zone'
                    log_method="1ez-ExitZone"

                #entered 'other' zone
                else:
                    interval = 240
                    log_method="1zc-ZoneChanged"

                log_msg = (f"Zone-{zone}, Last-{self.state_last_poll.get(devicename)}, "
                           f"This-{self.state_this_poll.get(devicename)}")
                self.log_debug_interval_msg(devicename, log_msg)

            #inzone & poor gps & check gps accuracy when inzone
            elif (self.poor_gps_accuracy_flag.get(devicename) and
                    inzone_flag and self.check_gps_accuracy_inzone_flag):
                interval   = 300      #poor accuracy, try again in 5 minutes
                log_method = '2iz-PoorGPS'

            elif self.poor_gps_accuracy_flag.get(devicename):
                interval = self._get_interval_for_error_retry_cnt(
                                self.old_loc_poor_gps_cnt.get(devicename))
                log_method = '2niz-PoorGPS'

            elif self.overrideinterval_seconds.get(devicename) > 0:
                interval   = self.overrideinterval_seconds.get(devicename)
                log_method = '3-Override'

            elif (STATIONARY in zone):
                interval = self.stat_zone_inzone_interval
                log_method = "4sz-Stationary"
                log_msg    = f"Zone-{zone}"

            elif location_isold_flag:
                interval = self._get_interval_for_error_retry_cnt(
                                self.old_loc_poor_gps_cnt.get(devicename))
                log_method = '4-OldLoc'
                log_msg      = f"Cnt-{self.old_loc_poor_gps_cnt.get(devicename)}"

            elif (inzone_home_flag or
                    (dist_from_zone_km < .05 and dir_of_travel == 'towards')):
                interval   = self.inzone_interval
                log_method = '4iz-InZone'
                log_msg    = f"Zone-{zone}"

            elif zone == 'near_zone':
                interval = 15
                log_method = '4nz-NearZone'
                log_msg    = f"Zone-{zone}, Dir-{dir_of_travel}"

            #in another zone and inzone time > travel time
            elif (inzone_flag and self.inzone_interval > waze_interval):
                interval   = self.inzone_interval
                log_method = '4iz-InZone'
                log_msg    = f"Zone-{zone}"

            elif dir_of_travel in ('left_zone', NOT_SET):
                interval = 150
                if inzone_home_flag:
                    dir_of_travel = AWAY_FROM
                else:
                    dir_of_travel = NOT_SET
                log_method = '5-NeedInfo'
                log_msg    = f"ZoneLeft-{zone}"


            elif dist_from_zone_km < 2.5 and self.went_3km.get(devicename):
                interval   = 15             #1.5 mi=real close and driving
                log_method = '10a-Dist < 2.5km(1.5mi)'

            elif dist_from_zone_km < 3.5:      #2 mi=30 sec
                interval   = 30
                log_method = '10b-Dist < 3.5km(2mi)'

            elif waze_time_from_zone > 5 and waze_interval > 0:
                interval   = waze_interval
                log_method = '10c-WazeTime'
                log_msg    = f"TimeFmHome-{waze_time_from_zone}"

            elif dist_from_zone_km < 5:        #3 mi=1 min
                interval   = 60
                log_method = '10d-Dist < 5km(3mi)'

            elif dist_from_zone_km < 8:        #5 mi=2 min
                interval   = 120
                log_method = '10e-Dist < 8km(5mi)'

            elif dist_from_zone_km < 12:       #7.5 mi=3 min
                interval   = 180
                log_method = '10f-Dist < 12km(7mi)'


            elif dist_from_zone_km < 20:       #12 mi=10 min
                interval   = 600
                log_method = '10g-Dist < 20km(12mi)'

            elif dist_from_zone_km < 40:       #25 mi=15 min
                interval   = 900
                log_method = '10h-Dist < 40km(25mi)'

            elif dist_from_zone_km > 150:      #90 mi=1 hr
                interval   = 3600
                log_method = '10i-Dist > 150km(90mi)'

            else:
                interval   = calc_interval
                log_method = '20-Calculated'
                log_msg    = f"Value-{self._km_to_mi(dist_from_zone_km)}/1.5"
        except Exception as err:
            attrs_msg = self._internal_error_msg(fct_name, err, 'SetInterval')

        try:
            #if haven't moved far for 8 minutes, put in stationary zone
            #determined in get_dist_data with dir_of_travel
            if dir_of_travel == STATIONARY:
                interval = self.stat_zone_inzone_interval
                log_method = "21-Stationary"

                if self.in_stationary_zone_flag.get(devicename) is False:
                    rtn_code = self._update_stationary_zone(
                        devicename,
                        latitude,
                        longitude,
                        STATIONARY_ZONE_VISIBLE)

                    self.in_stationary_zone_flag[devicename] = rtn_code
                    if rtn_code:
                        self.zone_current[devicename]   = self._format_zone_name(devicename, STATIONARY)
                        self.zone_timestamp[devicename] = dt_util.now().strftime(self.um_date_time_strfmt)
                        log_method_im   = "●Set.Stationary.Zone"
                        zone            = STATIONARY
                        dir_of_travel   = 'in_zone'
                        inzone_flag     = True
                        not_inzone_flag = False
                    else:
                        dir_of_travel = NOT_SET

            if dir_of_travel in ('', AWAY_FROM) and interval < 180:
                interval = 180
                log_method_im = '30-Away(<3min)'

            elif (dir_of_travel == AWAY_FROM and
                    not self.distance_method_waze_flag):
                interval_multiplier = 2    #calc-increase timer
                log_method_im = '30-Away(Calc)'

            elif (dir_of_travel == NOT_SET and interval > 180):
                interval = 180

            #15-sec interval (close to zone) and may be going into a stationary zone,
            #increase the interval
            elif (interval == 15 and
                    devicename in self.stat_zone_timer and
                    self.this_update_secs >= self.stat_zone_timer.get(devicename)+45):
                interval = 30
                log_method_im = '31-StatTimer+45'

        except Exception as err:
            attrs_msg = self._internal_error_msg(fct_name, err, 'SetStatZone')
            _LOGGER.exception(err)


        try:
            #Turn off waze close to zone flag to use waze after leaving zone
            if inzone_flag:
                self.waze_close_to_zone_pause_flag = False

            #if triggered by ios app (Zone Enter/Exit, Manual, Fetch, etc.)
            #and interval < 3 min, set to 3 min. Leave alone if > 3 min.
            if (self.iosapp_update_flag.get(devicename) and
                    interval < 180 and
                    self.overrideinterval_seconds.get(devicename) == 0):
                interval   = 180
                log_method = '0-iosAppTrigger'

            #no longer in stationary, reset stat zone size but keep in old position
            if (not_inzone_flag and self.in_stationary_zone_flag.get(devicename)):
                self.in_stationary_zone_flag[devicename] = False

                zone_name = self._format_zone_name(devicename, STATIONARY)
                rtn_code = self._update_stationary_zone(
                    devicename,
                    self.zone_lat.get(zone_name),
                    self.zone_long.get(zone_name),
                    STATIONARY_ZONE_HIDDEN)
                self._save_event(devicename, "Stationary Zone Exited")

            #if changed zones on this poll reset multiplier
            if self.state_change_flag.get(devicename):
                interval_multiplier = 1

            #Check accuracy again to make sure nothing changed, update counter
            if self.poor_gps_accuracy_flag.get(devicename):
                interval_multiplier = 1

        except Exception as err:
            attrs_msg = self._internal_error_msg(fct_name, err, 'ResetStatZone')
            return attrs_msg


        try:
            #Real close, final check to make sure interval is not adjusted
            if interval <= 60 or \
                    (battery > 0 and battery <= 33 and interval >= 120):
                interval_multiplier = 1

            interval     = interval * interval_multiplier
            interval, x  = divmod(interval, 15)
            interval     = interval * 15
            interval_str = self._secs_to_time_str(interval)

            interval_debug_msg = (f"●Interval-{interval_str} ({log_method}, {log_msg}), "
                                  f"●DirOfTrav-{dir_of_trav_msg}, "
                                  f"●State-{self.state_last_poll.get(devicename)}->, "
                                  f"{self.state_this_poll.get(devicename)}, "
                                  f"Zone-{zone}")
            event_msg = (f"Interval basis: {log_method}, {log_msg}, Direction {dir_of_travel}")
            #self._save_event(devicename, event_msg)

            if interval_multiplier != 1:
               interval_debug_msg = (f"{interval_debug_msg}, "
                                     f"Multiplier-{interval_multiplier}({log_method_im})")

                        #check if next update is past midnight (next day), if so, adjust it
            next_poll = round((self.this_update_secs + interval)/15, 0) * 15

            # Update all dates and other fields
            self.next_update_secs[devicename_zone] = next_poll
            self.next_update_time[devicename_zone] = self._secs_to_time(next_poll)
            self.interval_seconds[devicename_zone] = interval
            self.interval_str[devicename_zone]     = interval_str
            self.last_update_secs[devicename_zone] = self.this_update_secs
            self.last_update_time[devicename_zone] = self._secs_to_time(self.this_update_secs)

        #--------------------------------------------------------------------------------
            #Calculate the old_location age check based on the direction and if there are
            #multiple zones being tracked from

            zi=self.track_from_zone.get(devicename).index(self.base_zone)
            if zi == 0:
                self.old_location_secs[devicename] = HIGH_INTEGER

            dev_old_location_secs = self.old_location_secs.get(devicename)
            new_old_location_secs = self._determine_old_location_secs(zone, interval)
            select=''
            if inzone_flag:
                select='inzone'
                dev_old_location_secs = new_old_location_secs

            #Other base_zones are calculated before home zone, use smallest value
            elif new_old_location_secs < dev_old_location_secs:
                select='ols < self.ols'
                dev_old_location_secs = new_old_location_secs

            elif base_zone_home_flag and dev_old_location_secs == HIGH_INTEGER:
                select='zone-home & HIGH_INTEGER'
                dev_old_location_secs = new_old_location_secs

            self.old_location_secs[devicename] = dev_old_location_secs
            old_location_secs_msg = self._secs_to_time_str(self.old_location_secs.get(devicename))

        #--------------------------------------------------------------------------------
            #if more than 3km(1.8mi) then assume driving, used later above
            if dist_from_zone_km > 3:                # 1.8 mi
                self.went_3km[devicename] = True
            elif dist_from_zone_km < .03:            # home, reset flag
                 self.went_3km[devicename] = False

        except Exception as err:
            attrs_msg = self._internal_error_msg(fct_name, err, 'SetTimes')

        #--------------------------------------------------------------------------------
        try:
            log_msg = (f"►►INTERVAL FORMULA, {interval_debug_msg}")
            self.log_debug_interval_msg(devicename, log_msg)

            if self.log_level_intervalcalc_flag == False:
                interval_debug_msg = ''

            log_msg = (f"►DETERMINE INTERVAL <COMPLETE>, "
                f"This poll: {self._secs_to_time(self.this_update_secs)}({self.this_update_secs}), "
                f"Last Update: {self.last_update_time.get(devicename_zone)}({self.last_update_secs.get(devicename_zone)}), "
                f"Next Update: {self.next_update_time.get(devicename_zone)}({self.next_update_secs.get(devicename_zone)}), "
                f"Interval: {self.interval_str.get(devicename_zone)}*{interval_multiplier}, "
                f"OverrideInterval-{self.overrideinterval_seconds.get(devicename)}, "
                f"DistTraveled-{dist_last_poll_moved_km}, CurrZone-{zone}")
            self.log_debug_interval_msg(devicename, log_msg)

        except Exception as err:
            attrs_msg = self._internal_error_msg(fct_name, err, 'ShowMsgs')


        try:
            #if 'NearZone' zone, do not change the state
            if near_zone_flag:
                zone = NOT_HOME

            log_msg = (f"►DIR OF TRAVEL ATTRS, Direction-{dir_of_travel}, LastDir-{last_dir_of_travel}, "
               f"Dist-{dist_from_zone_km}, LastDist-{last_dist_from_zone_km}, "
               f"SelfDist-{self.zone_dist.get(devicename_zone)}, Moved-{dist_from_zone_moved_km},"
               f"WazeMoved-{waze_dist_from_zone_moved_km}")
            self.log_debug_interval_msg(devicename, log_msg)

            #if poor gps and moved less than 1km, redisplay last distances
            if (self.state_change_flag.get(devicename) == False and
                    self.poor_gps_accuracy_flag.get(devicename) and
                            dist_last_poll_moved_km < 1):
                dist_from_zone_km      = self.zone_dist.get(devicename_zone)
                waze_dist_from_zone_km = self.waze_dist.get(devicename_zone)
                calc_dist_from_zone_km = self.calc_dist.get(devicename_zone)
                waze_time_msg          = self.waze_time.get(devicename_zone)

            else:
                waze_time_msg          = self._format_waze_time_msg(waze_time_from_zone)

                #save for next poll if poor gps
                self.zone_dist[devicename_zone] = dist_from_zone_km
                self.waze_dist[devicename_zone] = waze_dist_from_zone_km
                self.waze_time[devicename_zone] = waze_time_msg
                self.calc_dist[devicename_zone] = calc_dist_from_zone_km

        except Exception as err:
            attrs_msg = self._internal_error_msg(fct_name, err, 'SetDistDir')

        #--------------------------------------------------------------------------------
        try:
            #Save last and new state, set attributes
            #If first time thru, set the last state to the current state
            #so a zone change will not be triggered next time
            if self.state_last_poll.get(devicename) == NOT_SET:
                self.state_last_poll[devicename] = zone

            #When put into stationary zone, also set last_poll so it
            #won't trigger again on next cycle as a state change
            #elif (zone.endswith(STATIONARY) or
            #        self.state_this_poll.get(devicename).endswith(STATIONARY)):
            elif (instr(zone, STATIONARY) or
                    instr(self.state_this_poll.get(devicename), STATIONARY)):
                zone                     = STATIONARY
                self.state_last_poll[devicename] = STATIONARY

            else:
                self.state_last_poll[devicename] = self.state_this_poll.get(devicename)

            self.state_this_poll[devicename]   = zone
            self.last_located_time[devicename] = self._time_to_12hrtime(location_time)
            location_age                       = self._secs_since(location_time_secs)
            location_age_str                   = self._secs_to_time_str(location_age)
            if location_isold_flag:
                location_age_str = (f"Old-{location_age_str}")

            log_msg =  (f"LOCATION TIME-{devicename} location_time-{location_time}, "
                        f"loc_time_secs-{self._secs_to_time(location_time_secs)}({location_time_secs}), "
                        f"age-{location_age_str}")
            self.log_debug_msg(devicename, log_msg)

            attrs = {}
            attrs[ATTR_ZONE]              = self.zone_current.get(devicename)
            attrs[ATTR_ZONE_TIMESTAMP]    = str(self.zone_timestamp.get(devicename))
            attrs[ATTR_LAST_ZONE]         = self.zone_last.get(devicename)
            attrs[ATTR_LAST_UPDATE_TIME]  = self._secs_to_time(self.this_update_secs)
            attrs[ATTR_LAST_LOCATED]      = self._time_to_12hrtime(location_time)

            attrs[ATTR_INTERVAL]          = interval_str
            attrs[ATTR_NEXT_UPDATE_TIME]  = self._secs_to_time(next_poll)

            attrs[ATTR_WAZE_TIME]     = ''
            if self.waze_status == WAZE_USED:
                attrs[ATTR_WAZE_TIME]     = waze_time_msg
                attrs[ATTR_WAZE_DISTANCE] = self._km_to_mi(waze_dist_from_zone_km)
            elif self.waze_status == WAZE_NOT_USED:
                attrs[ATTR_WAZE_DISTANCE] = 'NotUsed'
            elif self.waze_status == WAZE_NO_DATA:
                attrs[ATTR_WAZE_DISTANCE] = 'NoData'
            elif self.waze_status == WAZE_OUT_OF_RANGE:
                if waze_dist_from_zone_km < 1:
                    attrs[ATTR_WAZE_DISTANCE] = ''
                elif waze_dist_from_zone_km < self.waze_min_distance:
                    attrs[ATTR_WAZE_DISTANCE] = 'DistLow'
                else:
                    attrs[ATTR_WAZE_DISTANCE] = 'DistHigh'
            elif dir_of_travel == 'in_zone':
                attrs[ATTR_WAZE_DISTANCE] = ''
            elif self.waze_status == WAZE_PAUSED:
                attrs[ATTR_WAZE_DISTANCE] = PAUSED
            elif waze_dist_from_zone_km > 0:
                attrs[ATTR_WAZE_TIME]     = waze_time_msg
                attrs[ATTR_WAZE_DISTANCE] = self._km_to_mi(waze_dist_from_zone_km)
            else:
                attrs[ATTR_WAZE_DISTANCE] = ''

            attrs[ATTR_ZONE_DISTANCE]   = self._km_to_mi(dist_from_zone_km)
            attrs[ATTR_CALC_DISTANCE]   = self._km_to_mi(calc_dist_from_zone_km)
            attrs[ATTR_DIR_OF_TRAVEL]   = dir_of_travel
            attrs[ATTR_TRAVEL_DISTANCE] = self._km_to_mi(dist_last_poll_moved_km)

            info_msg = self._format_info_attr(
                    devicename,
                    battery,
                    gps_accuracy,
                    dist_last_poll_moved_km,
                    zone,
                    location_isold_flag, location_time_secs)
                    #location_time)

            attrs[ATTR_INFO] = interval_debug_msg + info_msg

            #save for event log
            self.last_tavel_time[devicename_zone]   = waze_time_msg
            self.last_distance_str[devicename_zone] = (f"{self._km_to_mi(dist_from_zone_km)} {self.unit_of_measurement}")
            self._trace_device_attributes(devicename, 'Results', fct_name, attrs)

            event_msg = (f"Results: {self.zone_fname.get(self.base_zone)} > "
                         f"CurrZone-{self.zone_fname.get(self.zone_current.get(devicename), AWAY)}, "
                         f"GPS-{format_gps(latitude, longitude)}, "
                         f"Interval-{interval_str}, "
                         f"Dist-{self._km_to_mi(dist_from_zone_km)} {self.unit_of_measurement}, "
                         f"TravTime-{waze_time_msg} ({dir_of_travel}), "
                         f"NextUpdt-{self._secs_to_time(next_poll)}, "
                         f"Located-{self._time_to_12hrtime(location_time)} ({location_age_str} ago), "
                         f"OldLocThreshold-{old_location_secs_msg}")
            self._save_event_halog_debug(devicename, event_msg)

            return attrs

        except Exception as err:
            attrs_msg = self._internal_error_msg(fct_name, err, 'SetAttrs')
            _LOGGER.exception(err)
            return attrs_msg

#########################################################
#
#   iCloud FmF or FamShr authentication returned an error or no location
#   data is available. Update counter and device attributes and set
#   retry intervals based on current retry count.
#
#########################################################
    def _determine_interval_retry_after_error(self, devicename, retry_cnt, info_msg):
        '''
        Handle errors where the device can not be or should not be updated with
        the current data. The update will be retried 4 times on a 15 sec interval.
        If the error continues, the interval will increased based on the retry
        count using the following cycles:
            1-4   - 15 sec
            5-8   - 1 min
            9-12  - 5min
            13-16 - 15min
            >16   - 30min

        The following errors use this routine:
            - iCloud Authentication errors
            - FmF location data not available
            - Old location
            - Poor GPS Acuracy
        '''

        fct_name = "_determine_interval_retry_after_error"

        base_zone_home_flag = (self.base_zone == HOME)
        devicename_zone = self._format_devicename_zone(devicename)

        try:
            interval = self._get_interval_for_error_retry_cnt(retry_cnt)

            #check if next update is past midnight (next day), if so, adjust it
            next_poll = round((self.this_update_secs + interval)/15, 0) * 15

            # Update all dates and other fields
            interval_str  = self._secs_to_time_str(interval)
            next_updt_str = self._secs_to_time(next_poll)
            last_updt_str = self._secs_to_time(self.this_update_secs)

            self.interval_seconds[devicename_zone] = interval
            self.last_update_secs[devicename_zone] = self.this_update_secs
            self.next_update_secs[devicename_zone] = next_poll
            self.last_update_time[devicename_zone] = last_updt_str
            self.next_update_time[devicename_zone] = next_updt_str
            self.interval_str[devicename_zone]     = interval_str
            self.count_update_ignore[devicename]  += 1

            attrs = {}
            attrs[ATTR_LAST_UPDATE_TIME] = last_updt_str
            attrs[ATTR_INTERVAL]         = interval_str
            attrs[ATTR_NEXT_UPDATE_TIME] = next_updt_str
            attrs[ATTR_POLL_COUNT]       = self._format_poll_count(devicename)
            attrs[ATTR_INFO]             = "●" + info_msg

            this_zone = self.state_this_poll.get(devicename)
            this_zone = self._format_zone_name(devicename, this_zone)
            last_zone = self.state_last_poll.get(devicename)
            last_zone = self._format_zone_name(devicename, last_zone)

            if self._is_inzone(devicename):
                latitude  = self.zone_lat.get(this_zone)
                longitude = self.zone_long.get(this_zone)

            elif self._was_inzone(devicename):
                latitude  = self.zone_lat.get(last_zone)
                longitude = self.zone_long.get(last_zone)
            else:
                latitude  = self.last_lat.get(devicename)
                longitude = self.last_long.get(devicename)

            if latitude == None or longitude == None:
                latitude  = self.last_lat.get(devicename)
                longitude = self.last_long.get(devicename)
            if latitude == None or longitude == None:
                latitude  = self.zone_lat.get(last_zone)
                longitude = self.zone_long.get(last_zone)
            if latitude == None or longitude == None:
                event_msg = "Aborting update, no location data"
                self._save_event_halog_error(devicename,event_msg)
                return

            kwargs = self._setup_base_kwargs(devicename,
                latitude, longitude, 0, 0)

            self._update_device_sensors(devicename, kwargs)
            self._update_device_sensors(devicename, attrs)
            self._update_device_attributes(devicename, kwargs, attrs, 'DetIntlErrorRetry')

            self.device_being_updated_flag[devicename] = False

            log_msg = (f"►DETERMINE INTERVAL ERROR RETRY, CurrZone-{this_zone}, "
                f"LastZone-{last_zone}, GPS-{format_gps(latitude,longitude)}")
            self.log_debug_interval_msg(devicename, log_msg)
            log_msg = (f"►DETERMINE INTERVAL ERROR RETRY, Interval-{interval_str}, "
                f"LastUpdt-{last_updt_str}, NextUpdt-{next_updt_str}, Info-{info_msg}")
            self.log_debug_interval_msg(devicename, log_msg)

        except Exception as err:
            _LOGGER.exception(err)

#########################################################
#
#   UPDATE DEVICE LOCATION & INFORMATION ATTRIBUTE FUNCTIONS
#
#########################################################
    def _get_distance_data(self, devicename, latitude, longitude,
                                gps_accuracy, location_isold_flag):
        """ Determine the location of the device.
            Returns:
                - zone (current zone from lat & long)
                  set to HOME if distance < home zone radius
                - dist_from_zone_km (mi or km)
                - dist_traveled (since last poll)
                - dir_of_travel (towards, away_from, stationary, in_zone,
                                       left_zone, near_home)
        """

        fct_name = '_get_distance_data'

        try:
            if latitude == None or longitude == None:
                attrs = self._internal_error_msg(fct_name, 'lat/long=None', 'NoLocation')
                return ('ERROR', attrs)

            base_zone_home_flag = (self.base_zone == HOME)
            devicename_zone = self._format_devicename_zone(devicename)

            log_msg = ("►GET DEVICE DISTANCE DATA Entered")
            self.log_debug_interval_msg(devicename, log_msg)

            last_dir_of_travel     = NOT_SET
            last_dist_from_zone_km = 0
            last_waze_time         = 0
            last_lat               = self.base_zone_lat
            last_long              = self.base_zone_long
            dev_timestamp_secs     = 0

            zone                         = self.base_zone
            calc_dist_from_zone_km       = 0
            calc_dist_last_poll_moved_km = 0
            calc_dist_from_zone_moved_km = 0


            #Get the devicename's icloud3 attributes
            entity_id = self.device_tracker_entity.get(devicename)
            attrs     = self._get_device_attributes(entity_id)

            self._trace_device_attributes(devicename, 'Read', fct_name, attrs)

        except Exception as err:
            _LOGGER.exception(err)
            error_msg = (f"Entity-{entity_id}, Err-{err}")
            attrs = self._internal_error_msg(fct_name, error_msg, 'GetAttrs')
            return ('ERROR', attrs)

        try:
            #Not available if first time after reset
            if self.state_last_poll.get(devicename) != NOT_SET:
                log_msg = ("Distance info available")
                if ATTR_TIMESTAMP in attrs:
                    dev_timestamp_secs = attrs[ATTR_TIMESTAMP]
                    dev_timestamp_secs = self._timestamp_to_time(dev_timestamp_secs)
                else:
                    dev_timestamp_secs = 0

                last_dist_from_zone_km_s = self._get_attr(attrs, ATTR_ZONE_DISTANCE, NUMERIC)
                last_dist_from_zone_km   = self._mi_to_km(last_dist_from_zone_km_s)

                last_waze_time        = self._get_attr(attrs, ATTR_WAZE_TIME)
                last_dir_of_travel    = self._get_attr(attrs, ATTR_DIR_OF_TRAVEL)
                last_dir_of_travel    = last_dir_of_travel.replace('*', '', 99)
                last_dir_of_travel    = last_dir_of_travel.replace('?', '', 99)
                last_lat              = self.last_lat.get(devicename)
                last_long             = self.last_long.get(devicename)

            #get last interval
            interval_str = self.interval_str.get(devicename_zone)
            interval     = self._time_str_to_secs(interval_str)

            this_lat  = latitude
            this_long = longitude

        except Exception as err:
            _LOGGER.exception(err)
            attrs = self._internal_error_msg(fct_name, err, 'SetupLocation')
            return ('ERROR', attrs)

        try:
            zone = self._get_zone(devicename, this_lat, this_long)

            log_msg =  (f"►LAT-LONG GPS INITIALIZED {zone}, LastDirOfTrav-{last_dir_of_travel}, "
                        f"LastGPS=({last_lat}, {last_long}), ThisGPS=({this_lat}, {this_long}), "
                        f"UsingGPS=({latitude}, {longitude}), GPS.Accur-{gps_accuracy}, "
                        f"GPS.Threshold-{self.gps_accuracy_threshold}")
            self.log_debug_interval_msg(devicename, log_msg)

        except Exception as err:
            _LOGGER.exception(err)
            attrs = self._internal_error_msg(fct_name, err, 'GetCurrZone')
            return ('ERROR', attrs)

        try:
            # Get Waze distance & time
            #   Will return [error, 0, 0, 0] if error
            #               [out_of_range, dist, time, info] if
            #                           last_dist_from_zone_km >
            #                           last distance from home
            #               [ok, 0, 0, 0]  if zone=home
            #               [ok, distFmHome, timeFmHome, info] if OK

            calc_dist_from_zone_km       = self._calc_distance_km(this_lat, this_long,
                                            self.base_zone_lat, self.base_zone_long)
            calc_dist_last_poll_moved_km = self._calc_distance_km(last_lat, last_long,
                                            this_lat, this_long)
            calc_dist_from_zone_moved_km= (calc_dist_from_zone_km - last_dist_from_zone_km)
            calc_dist_from_zone_km       = self._round_to_zero(calc_dist_from_zone_km)
            calc_dist_last_poll_moved_km = self._round_to_zero(calc_dist_last_poll_moved_km)
            calc_dist_from_zone_moved_km= self._round_to_zero(calc_dist_from_zone_moved_km)

            if self.distance_method_waze_flag:
                #If waze paused via icloud_command or close to a zone, default to pause
                if self.waze_manual_pause_flag or self.waze_close_to_zone_pause_flag:
                    self.waze_status = WAZE_PAUSED
                else:
                   self.waze_status = WAZE_USED
            else:
                self.waze_status = WAZE_NOT_USED

            log_msg =  (f"Zone-{devicename_zone}, wStatus-{self.waze_status}, "
                        f"calc_dist-{calc_dist_from_zone_km}, wManualPauseFlag-{self.waze_manual_pause_flag}, "
                        f"CloseToZoneFlag-{self.waze_close_to_zone_pause_flag}")
            self.log_debug_interval_msg(devicename, log_msg)

            #Make sure distance and zone are correct for HOME, initialize
            if calc_dist_from_zone_km <= .05 or zone == self.base_zone:
                zone                 = self.base_zone
                calc_dist_from_zone_km       = 0
                calc_dist_last_poll_moved_km = 0
                calc_dist_from_zone_moved_km = 0
                self.waze_status             = WAZE_PAUSED

            #Near zone & towards or in near_zone
            elif (calc_dist_from_zone_km < 1 and
                    last_dir_of_travel in ('towards', 'near_zone')):
                self.waze_status = WAZE_PAUSED
                self.waze_close_to_zone_pause_flag = True

                log_msg = "Using Calc Method (near Home & towards or Waze off)"
                self.log_debug_interval_msg(devicename, log_msg)

            #Determine if Waze should be used based on calculated distance
            elif (calc_dist_from_zone_km > self.waze_max_distance or
                  calc_dist_from_zone_km < self.waze_min_distance):
                self.waze_status = WAZE_OUT_OF_RANGE

            #Initialize Waze default fields
            waze_dist_from_zone_km       = calc_dist_from_zone_km
            waze_time_from_zone          = 0
            waze_dist_last_poll_moved_km = calc_dist_last_poll_moved_km
            waze_dist_from_zone_moved_km = calc_dist_from_zone_moved_km
            self.waze_history_data_used_flag[devicename_zone] = False

            #Use Calc if close to home, Waze not accurate when close

            log_msg =  (f"Zone-{devicename_zone}, Status-{self.waze_status}, "
                        f"calc_dist-{calc_dist_from_zone_km}, "
                        f"ManualPauseFlag-{self.waze_manual_pause_flag},"
                        f"CloseToZoneFlag-{self.waze_close_to_zone_pause_flag}")
            self.log_debug_interval_msg(devicename, log_msg)

        except Exception as err:
            _LOGGER.exception(err)
            attrs = self._internal_error_msg(fct_name, err, 'InitializeDist')
            return ('ERROR', attrs)

        try:
            if self.waze_status == WAZE_USED:
                try:
                    #See if another device is close with valid Waze data.
                    #If so, use it instead of calling Waze again. event_msg will have
                    #msg for log file if history was used

                    waze_dist_time_info = self._get_waze_from_data_history(
                                                devicename,
                                                calc_dist_from_zone_km,
                                                this_lat,
                                                this_long)

                    #No Waze data from close device. Get it from Waze
                    if waze_dist_time_info == None:
                        waze_dist_time_info = self._get_waze_data(
                                                devicename,
                                                this_lat, this_long,
                                                last_lat, last_long,
                                                zone,
                                                last_dist_from_zone_km)

                    self.waze_status = waze_dist_time_info[0]

                    if self.waze_status == WAZE_USED:
                        waze_dist_from_zone_km       = waze_dist_time_info[1]
                        waze_time_from_zone          = waze_dist_time_info[2]
                        waze_dist_last_poll_moved_km = waze_dist_time_info[3]
                        waze_dist_from_zone_moved_km= round(waze_dist_from_zone_km
                                                    - last_dist_from_zone_km, 2)
                        waze_time_msg               = self._format_waze_time_msg(waze_time_from_zone)

                        #Save new Waze data or retimestamp data from another
                        #device.
                        if (gps_accuracy <= self.gps_accuracy_threshold and
                                waze_dist_from_zone_km > 0 and
                                location_isold_flag is False):
                            self.waze_distance_history[devicename_zone] = \
                                    [self._time_now_secs(),
                                    this_lat,
                                    this_long,
                                    waze_dist_time_info]

                    else:
                        self.waze_distance_history[devicename_zone] = []

                except Exception as err:
                    _LOGGER.exception(err)
                    self.waze_status = WAZE_NO_DATA

        except Exception as err:
            attrs = self._internal_error_msg(fct_name, err, 'WazeNoData')
            self.waze_status = WAZE_NO_DATA

        try:
            #if self.waze_status == WAZE_NO_DATA:
            #    waze_dist_from_zone_km       = calc_dist_from_zone_km
            #    waze_time_from_zone          = 0
            #    waze_dist_last_poll_moved_km = calc_dist_last_poll_moved_km
            #    waze_dist_from_zone_moved_km = calc_dist_from_zone_moved_km
            #    self.waze_distance_history[devicename_zone] = []
            #    self.waze_history_data_used_flag[devicename_zone] = False

            #don't reset data if poor gps, use the best we have
            if zone == self.base_zone:
                distance_method         = 'Home/Calc'
                dist_from_zone_km       = 0
                dist_last_poll_moved_km = 0
                dist_from_zone_moved_km = 0
            elif self.waze_status == WAZE_USED:
                distance_method         = 'Waze'
                dist_from_zone_km       = waze_dist_from_zone_km
                dist_last_poll_moved_km = waze_dist_last_poll_moved_km
                dist_from_zone_moved_km = waze_dist_from_zone_moved_km
            else:
                distance_method         = 'Calc'
                dist_from_zone_km       = calc_dist_from_zone_km
                dist_last_poll_moved_km = calc_dist_last_poll_moved_km
                dist_from_zone_moved_km = calc_dist_from_zone_moved_km

            if dist_from_zone_km > 99: dist_from_zone_km = int(dist_from_zone_km)
            if dist_last_poll_moved_km > 99: dist_last_poll_moved_km = int(dist_last_poll_moved_km)
            if dist_from_zone_moved_km> 99: dist_from_zone_moved_km= int(dist_from_zone_moved_km)

            dist_from_zone_moved_km= self._round_to_zero(dist_from_zone_moved_km)

            log_msg = (f"►DISTANCES CALCULATED, "
                       f"Zone-{zone}, Method-{distance_method}, "
                       f"LastDistFmHome-{last_dist_from_zone_km}, "
                       f"WazeStatus-{self.waze_status}")
            self.log_debug_interval_msg(devicename, log_msg)
            log_msg = (f"►DISTANCES ...Waze, "
                       f"Dist-{waze_dist_from_zone_km}, "
                       f"LastPollMoved-{waze_dist_last_poll_moved_km}, "
                       f"FmHomeMoved-{waze_dist_from_zone_moved_km}, "
                       f"Time-{waze_time_from_zone}, "
                       f"Status-{self.waze_status}")
            self.log_debug_interval_msg(devicename, log_msg)
            log_msg = (f"►DISTANCES ...Calc, "
                       f"Dist-{calc_dist_from_zone_km}, "
                       f"LastPollMoved-{calc_dist_last_poll_moved_km}, "
                       f"FmHomeMoved-{calc_dist_from_zone_moved_km}")
            self.log_debug_interval_msg(devicename, log_msg)

            #if didn't move far enough to determine towards or away_from,
            #keep the current distance and add it to the distance on the next
            #poll
            if (dist_from_zone_moved_km> -.3 and dist_from_zone_moved_km< .3):
                dist_from_zone_moved_km+= \
                        self.dist_from_zone_km_small_move_total.get(devicename)
                self.dist_from_zone_km_small_move_total[devicename] = \
                        dist_from_zone_moved_km
            else:
                 self.dist_from_zone_km_small_move_total[devicename] = 0

        except Exception as err:
            _LOGGER.exception(err)
            attrs = self._internal_error_msg(fct_name, err, 'CalcDist')
            return ('ERROR', attrs)

        try:
            section = "dir_of_trav"
            dir_of_travel   = ''
            dir_of_trav_msg = ''
            if zone not in (NOT_HOME, 'near_zone'):
                dir_of_travel   = 'in_zone'
                dir_of_trav_msg = (f"Zone-{zone}")

            elif last_dir_of_travel == "in_zone":
                dir_of_travel   = 'left_zone'
                dir_of_trav_msg = (f"LastZone-{last_dir_of_travel}")

            elif dist_from_zone_moved_km<= -.3:            #.18 mi
                dir_of_travel   = 'towards'
                dir_of_trav_msg = (f"Dist-{dist_from_zone_moved_km}")

            elif dist_from_zone_moved_km>= .3:             #.18 mi
                dir_of_travel   = AWAY_FROM
                dir_of_trav_msg = (f"Dist-{dist_from_zone_moved_km}")

            elif self.poor_gps_accuracy_flag.get(devicename):
                dir_of_travel   = 'Poor.GPS'
                dir_of_trav_msg = ("Poor.GPS-{gps_accuracy}")

            else:
                #didn't move far enough to tell current direction
                dir_of_travel   = (f"{last_dir_of_travel}?")
                dir_of_trav_msg = (f"Moved-{dist_last_poll_moved_km}")
            #If moved more than stationary zone limit (~.06km(200ft)),
            #reset check StatZone 5-min timer and check again next poll
            #Use calc distance rather than waze for better accuracy
            section = "test if home"
            if (calc_dist_from_zone_km > self.stat_min_dist_from_zone_km and
                zone == NOT_HOME):

                section = "test moved"
                reset_stat_zone_flag = False
                if devicename not in self.stat_zone_moved_total:
                    reset_stat_zone_flag = True

                elif (calc_dist_last_poll_moved_km > self.stat_dist_move_limit):
                    reset_stat_zone_flag = True

                if reset_stat_zone_flag:
                    section = "test moved-reset stat zone "
                    self.stat_zone_moved_total[devicename] = 0
                    self.stat_zone_timer[devicename] = \
                        self.this_update_secs + self.stat_zone_still_time

                    log_msg = (f"►STATIONARY ZONE, Reset timer, "
                        f"Moved-{calc_dist_last_poll_moved_km}, "
                        f"Timer-{self._secs_to_time(self.stat_zone_timer.get(devicename))}")
                    self.log_debug_interval_msg(devicename, log_msg)

                #If moved less than the stationary zone limit, update the
                #distance moved and check to see if now in a stationary zone
                elif devicename in self.stat_zone_moved_total:
                    section = "StatZonePrep"
                    move_into_stationary_zone_flag = False
                    self.stat_zone_moved_total[devicename] += calc_dist_last_poll_moved_km
                    stat_zone_timer_left       = self.stat_zone_timer.get(devicename) - self.this_update_secs
                    stat_zone_timer_close_left = stat_zone_timer_left - self.stat_zone_still_time/2

                    log_msg = (f"►STATIONARY ZONE, Small movement check, "
                        f"TotalMoved-{self.stat_zone_moved_total.get(devicename)}, "
                        f"Timer-{self._secs_to_time(self.stat_zone_timer.get(devicename))}, "
                        f"TimerLeft-{stat_zone_timer_left}, "
                        f"CloseTimerLeft-{stat_zone_timer_close_left}, "
                        f"DistFmZone-{dist_from_zone_km}, "
                        f"CloseDist-{self.zone_radius_km.get(self.base_zone)*4}")
                    self.log_debug_interval_msg(devicename, log_msg)

                    section = "CheckNowInStatZone"

                    #See if moved less than the stationary zone movement limit
                    if self.stat_zone_moved_total.get(devicename) <= self.stat_dist_move_limit:
                        #See if time has expired
                        if stat_zone_timer_left <= 0:
                            move_into_stationary_zone_flag = True

                        #See if close to zone and 1/2 of the timer is left
                        elif (dist_from_zone_km <= self.zone_radius_km.get(self.base_zone)*4 and
                              (stat_zone_timer_close_left <= 0)):
                            move_into_stationary_zone_flag = True

                    #If updating via the ios app and the current state is stationary,
                    #make sure it is kept in the stationary zone
                    elif (self.iosapp_update_flag.get(devicename) and
                          self.state_this_poll.get(devicename) == STATIONARY):
                        move_into_stationary_zone_flag = True

                    if move_into_stationary_zone_flag:
                        dir_of_travel   = STATIONARY
                        dir_of_trav_msg = (f"Age-{self._secs_to(self.stat_zone_timer.get(devicename))}s, "
                                           f"Moved-{self.stat_zone_moved_total.get(devicename)}")
                else:
                    self.stat_zone_moved_total[devicename] = 0

            section = "Finalize"
            dir_of_trav_msg = (f"{dir_of_travel}({dir_of_trav_msg})")
            log_msg = (f"►DIR OF TRAVEL DETERMINED, {dir_of_trav_msg}")
            self.log_debug_interval_msg(devicename, log_msg)

            dist_from_zone_km            = self._round_to_zero(dist_from_zone_km)
            dist_from_zone_moved_km      = self._round_to_zero(dist_from_zone_moved_km)
            dist_last_poll_moved_km      = self._round_to_zero(dist_last_poll_moved_km)
            waze_dist_from_zone_km       = self._round_to_zero(waze_dist_from_zone_km)
            calc_dist_from_zone_moved_km = self._round_to_zero(calc_dist_from_zone_moved_km)
            waze_dist_last_poll_moved_km = self._round_to_zero(waze_dist_last_poll_moved_km)
            calc_dist_last_poll_moved_km = self._round_to_zero(calc_dist_last_poll_moved_km)
            last_dist_from_zone_km       = self._round_to_zero(last_dist_from_zone_km)

            log_msg = (f"►GET DEVICE DISTANCE DATA Complete, "
                        f"CurrentZone-{zone}, DistFmHome-{dist_from_zone_km}, "
                        f"DistFmHomeMoved-{dist_from_zone_moved_km}, "
                        f"DistLastPollMoved-{dist_last_poll_moved_km}")
            self.log_debug_interval_msg(devicename, log_msg)

            distance_data = (zone,
                             dir_of_travel,
                             dist_from_zone_km,
                             dist_from_zone_moved_km,
                             dist_last_poll_moved_km,
                             waze_dist_from_zone_km,
                             calc_dist_from_zone_km,
                             waze_dist_from_zone_moved_km,
                             calc_dist_from_zone_moved_km,
                             waze_dist_last_poll_moved_km,
                             calc_dist_last_poll_moved_km,
                             waze_time_from_zone,
                             last_dist_from_zone_km,
                             last_dir_of_travel,
                             dir_of_trav_msg,
                             dev_timestamp_secs)

            log_msg = (f"►DISTANCE DATA-{devicename}-{distance_data}")
            self.log_debug_msg(devicename, log_msg)

            return  distance_data

        except Exception as err:
           _LOGGER.exception(err)
           attrs = self._internal_error_msg(fct_name+section, err, 'Finalize')
           return ('ERROR', attrs)

#--------------------------------------------------------------------------------
    def _determine_old_location_secs(self, zone, interval):
        """
        Calculate the time between the location timestamp and now (age) a
        location record must be before it is considered old
        """
        if self.old_location_threshold > 0:
            return self.old_location_threshold

        old_location_secs = 14
        if self._is_inzoneZ(zone):
            old_location_secs = interval * .025     #inzone --> 2.5%
            if old_location_secs < 90: old_location_secs = 90

        elif interval < 90:
            old_location_secs = 15                  #15 secs if < 1.5 min

        else:
            old_location_secs = interval * .125    #12.5% of the interval

        if old_location_secs < 15:
            old_location_secs = 15
        elif old_location_secs > 600:
            old_location_secs = 600

        #IOS App old location time minimum is 3 min
        if self.TRK_METHOD_IOSAPP and old_location_secs < 180:
            old_location_secs == 180

        return old_location_secs

#########################################################
#
#    DEVICE ATTRIBUTES ROUTINES
#
#########################################################
    def _get_state(self, entity_id):
        """
        Get current state of the device_tracker entity
        (home, away, other state)
        """

        try:
            device_state = self.hass.states.get(entity_id).state

            if device_state:
                if device_state.lower() == 'not set':
                    state = NOT_SET
                else:
                    state = device_state
            else:
                state = NOT_HOME

        except Exception as err:
            #When starting iCloud3, the device_tracker for the iosapp might
            #not have been set up yet. Catch the entity_id error here.
            #_LOGGER.exception(err)
            state = NOT_SET

        return state.lower()
#--------------------------------------------------------------------
    def _get_entity_last_changed_time(self, entity_id):
        """
        Get entity's last changed time attribute
        Last changed time format '2019-09-09 14:02:45.12345+00:00' (utc value)
        Return time, seconds, timestamp
        """

        try:
            timestamp_utc = str(self.hass.states.get(entity_id).last_changed)

            timestamp_utc = timestamp_utc.split(".")[0]
            secs          = self._timestamp_to_secs(timestamp_utc, UTC_TIME)
            hhmmss        = self._secs_to_time(secs)
            timestamp     = self._secs_to_timestamp(secs)

            return hhmmss, secs, timestamp

        except Exception as err:
            _LOGGER.exception(err)
            return '', 0, TIMESTAMP_ZERO
#--------------------------------------------------------------------
    def _get_device_attributes(self, entity_id):
        """ Get attributes of the device """

        try:
            dev_data  = self.hass.states.get(entity_id)
            dev_attrs = dev_data.attributes

            retry_cnt = 0
            while retry_cnt < 10:
                if dev_attrs:
                    break
                retry_cnt += 1
                log_msg = (f"No attribute data returned for {entity_id}. Retrying #{retry_cnt}")
                self.log_debug_msg('*', log_msg)

        except (KeyError, AttributeError):
            dev_attrs = {}
            pass

        except Exception as err:
            _LOGGER.exception(err)
            dev_attrs = {}
            dev_attrs[ATTR_TRIGGER] = (f"Error {err}")

        return dict(dev_attrs)

#--------------------------------------------------------------------
    @staticmethod
    def _get_attr(attributes, attribute_name, numeric = False):
        ''' Get an attribute out of the attrs attributes if it exists'''
        if attribute_name in attributes:
            return attributes[attribute_name]
        elif numeric:
            return 0
        else:
            return ''

#--------------------------------------------------------------------
    def _update_device_attributes(self, devicename, kwargs: str = None,
                        attrs: str = None, fct_name: str = 'Unknown'):
        """
        Update the device and attributes with new information
        On Entry, kwargs = {} or contains the base attributes.

        Trace the interesting attributes if debugging.

        Full set of attributes is:
        'gps': (27.726639, -80.3904565), 'battery': 61, 'gps_accuracy': 65.0
        'dev_id': 'lillian_iphone', 'host_name': 'Lillian',
        'location_name': HOME, 'source_type': 'gps',
        'attributes': {'interval': '2 hrs', 'last_update': '10:55:17',
        'next_update': '12:55:15', 'travel_time': '', 'distance': 0,
        'calc_distance': 0, 'waze_distance': 0, 'dir_of_travel': 'in_zone',
        'travel_distance': 0, 'info': ' ●Battery-61%',
        'group': 'gary_icloud', 'authenticated': '02/22/19 10:55:10',
        'last_located': '10:55:15', 'device_status': 'online',
        ATTR_LOW_POWER_MODE: False, 'battery_status': 'Charging',
        'tracked_devices': 'gary_icloud/gary_iphone,
        gary_icloud/lillian_iphone', 'trigger': 'iCloud',
        'timestamp': '2019-02-22T10:55:17.543', 'poll_count': '1:0:1'}

        {'source_type': 'gps', 'latitude': 27.726639, 'longitude': -80.3904565,
        'gps_accuracy': 65.0, 'battery': 93, 'zone': HOME,
        'last_zone': HOME, 'zone_timestamp': '03/13/19, 9:47:35',
        'trigger': 'iCloud', 'timestamp': '2019-03-13T09:47:35.405',
        'interval': '2 hrs', 'travel_time': '', 'distance': 0,
        'calc_distance': 0, 'waze_distance': '', 'last_located': '9:47:34',
        'last_update': '9:47:35', 'next_update': '11:47:30',
        'poll_count': '1:0:2', 'dir_of_travel': 'in_zone',
        'travel_distance': 0, 'info': ' ●Battery-93%',
        'battery_status': 'NotCharging', 'device_status':
        'online', ATTR_LOW_POWER_MODE: False,
        'authenticated': '03/13/19, 9:47:26',
        'tracked_devices': 'gary_icloud/gary_iphone, gary_icloud/lillian_iphone',
        'group': 'gary_icloud', 'friendly_name': 'Gary',
        'icon': 'mdi:cellphone-iphone',
        'entity_picture': '/local/gary-caller_id.png'}
        """

        state        = self.state_this_poll.get(devicename)
        zone = self.zone_current.get(devicename)


        #######################################################################
        #The current zone is based on location of the device after it is looked
        #up in the zone tables.
        #The state is from the original trigger value when the poll started.
        #If the device went from one zone to another zone, an enter/exit trigger
        #may not have been issued. If the trigger was the next update time
        #reached, the state and zone many now not match. (v2.0.2)

        if state == NOT_SET or zone == NOT_SET or zone == '':
            pass

        #If state is 'stationary' and in a stationary zone, nothing to do
        elif state == STATIONARY and instr(zone, STATIONARY):
            pass

        #If state is 'stationary' and in another zone, reset the state to the
        #current zone that was based on the device location.
        #If the state is in a zone but not the current zone, change the state
        #to the current zone that was based on the device location.
        elif ((state == STATIONARY and self._is_inzone(zone)) or
                (self._is_inzone(state) and self._is_inzone(zone) and
                    state != zone)):
            event_msg = (f"State/Zone mismatch > Setting `state` value ({state}) "
                    "to `zone` value ({zone})")
            self._save_event(devicename, event_msg)
            state = zone

        #Test Code start
        if state == NOT_SET or zone == NOT_SET or zone == '':
            pass

        #Get friendly name or capitalize and reformat state,
        if self._is_inzoneZ(state):
            if self.zone_fname.get(state):
                state = self.zone_fname.get(state)

            else:
                state = state.replace('_', ' ', 99)
                state = state.title()

            if state == 'Home':
                state = HOME

        #Update the device timestamp
        if not attrs:
            attrs  = {}
        if ATTR_TIMESTAMP in attrs:
            timestamp = attrs[ATTR_TIMESTAMP]
        else:
            timestamp = dt_util.now().strftime(ATTR_TIMESTAMP_FORMAT)[0:19]
            attrs[ATTR_TIMESTAMP] = timestamp

        #Calculate and display how long the update took
        update_took_time =  round(time.time() - self.update_timer.get(devicename), 2)
        if update_took_time > 3 and ATTR_INFO in attrs:
            attrs[ATTR_INFO] = f"{attrs[ATTR_INFO]} ●Took {update_took_time}s"

        attrs[ATTR_NAME]            = self.fname.get(devicename)
        #attrs[ATTR_AUTHENTICATED]   = self._secs_to_timestamp(self.authenticated_time)
        attrs[ATTR_GROUP]           = self.group
        attrs[ATTR_TRACKING]        = self.track_devicename_list
        attrs[ATTR_ICLOUD3_VERSION] = VERSION

        #Add update time to trigger to be able to detect trigger change by iOS App
        #and by iC3.
        new_trigger = (f"{self.trigger.get(devicename)}@").split('@')[0]
        new_trigger = (f"{new_trigger}@{self.last_located_time.get(devicename)}")

        self.trigger[devicename] = new_trigger
        attrs[ATTR_TRIGGER]      = new_trigger

        #Update sensor.<devicename>_last_update_trigger if IOS App v2 detected
        #and iCloud3 has been running for at least 10 secs to let HA &
        #mobile_app start up to avoid error if iC3 loads before the mobile_app
        try:
            if self.iosapp_version.get(devicename) == 2:
            #if self.this_update_secs >= self.icloud3_started_secs + 10:
                sensor_entity = (f"sensor.{self.iosapp_v2_last_trigger_entity.get(devicename)}")
                sensor_attrs = {}
                state_value  = self.trigger.get(devicename)
                self.hass.states.set(sensor_entity, state_value, sensor_attrs)

        except:
            pass

        #Set the gps attribute and update the attributes via self.see
        if kwargs == {} or not kwargs:
            kwargs = self._setup_base_kwargs(
                devicename,
                self.last_lat.get(devicename),
                self.last_long.get(devicename),
                0, 0)

        kwargs['dev_id']        = devicename
        kwargs['host_name']     = self.fname.get(devicename)
        kwargs['location_name'] = state
        kwargs['source_type']   = 'gps'
        kwargs[ATTR_ATTRIBUTES] = attrs

        self.see(**kwargs)

        if state == "Not Set":
            state = "not_set"

        self.state_this_poll[devicename] = state.lower()

        self._trace_device_attributes(devicename, 'Write', fct_name, kwargs)

        if timestamp == '':         #Bypass if not initializing
            return

        retry_cnt = 1
        timestamp = timestamp[10:]      #Strip off date

        #Quite often, the attribute update has not actually taken
        #before other code is executed and errors occur.
        #Reread the attributes of the ones just updated to make sure they
        #were updated corectly. Verify by comparing the timestamps. If
        #differet, retry the attribute update. HA runs in multiple threads.
        try:
            entity_id = self.device_tracker_entity.get(devicename)
            while retry_cnt < 99:
                chk_see_attrs  = self._get_device_attributes(entity_id)
                chk_timestamp  = str(chk_see_attrs.get(ATTR_TIMESTAMP))
                chk_timestamp  = chk_timestamp[10:]

                if timestamp == chk_timestamp:
                    break

                log_msg = (f"Verify Check #{retry_cnt}. Expected {timestamp}, Read {chk_timestamp}")
                self.log_debug_msg(devicename, log_msg)

                #retry_cnt_msg = (f"Write Reread{retry_cnt}")
                #self._trace_device_attributes(
                #    devicename, retry_cnt_msg, fct_name, chk_see_attrs)

                if (retry_cnt % 10) == 0:
                    time.sleep(1)
                retry_cnt += 1

                self.see(**kwargs)

        except Exception as err:
            _LOGGER.exception(err)

        return

#--------------------------------------------------------------------
    def _setup_base_kwargs(self, devicename, latitude, longitude,
            battery, gps_accuracy):

        #check to see if device set up yet
        state = self.state_this_poll.get(devicename)
        zone_name = None

        if latitude == self.zone_home_lat:
            pass
        elif state == NOT_SET:
            zone_name = self.base_zone

        #if in zone, replace lat/long with zone center lat/long
        elif self._is_inzoneZ(state):
            zone_name = self._format_zone_name(devicename, state)

        debug_msg=(f"zone_name-{zone_name}, inzone-state-{self._is_inzoneZ(state)}")
        self.log_debug_msg(devicename, debug_msg)

        if zone_name and self._is_inzoneZ(state):
            zone_lat  = self.zone_lat.get(zone_name)
            zone_long = self.zone_long.get(zone_name)
            zone_dist = self._calc_distance_m(latitude, longitude, zone_lat, zone_long)

            debug_msg=(f"zone_lat/long=({zone_lat}, {zone_long}), "
                    f"lat-long=({latitude}, {longitude}), zone_dist-{zone_dist}, "
                    f"zone-radius-{self.zone_radius_km.get(zone_name, 100)}")
            self.log_debug_msg(devicename, debug_msg)

            #Move center of stationary zone to new location if more than 10m from old loc
            if instr(zone_name, STATIONARY) and zone_dist > 10:
                rtn_code = self._update_stationary_zone(
                        devicename,
                        latitude,
                        longitude,
                        STATIONARY_ZONE_VISIBLE)

            #inside zone, move to center
            elif (self.center_in_zone_flag and
                    zone_dist <= self.zone_radius_m.get(zone_name, 100) and
                    (latitude != zone_lat or longitude != zone_long)):
                event_msg  = (f"Moving to zone center > {zone_name}, "
                              f"GPS-{format_gps(latitude, longitude, zone_lat, zone_long)}, "
                              f"Distance-{self._format_dist_m(zone_dist)}")
                self._save_event(devicename, event_msg)
                self.log_debug_msg(devicename, event_msg)

                latitude  = zone_lat
                longitude = zone_long
                self.last_lat[devicename]  = zone_lat
                self.last_long[devicename] = zone_long

        gps_lat_long           = (latitude, longitude)
        kwargs                 = {}
        kwargs['gps']          = gps_lat_long
        kwargs[ATTR_BATTERY]   = int(battery)
        kwargs[ATTR_GPS_ACCURACY] = gps_accuracy

        return kwargs

#--------------------------------------------------------------------
    def _format_entity_id(self, devicename):
        return (f"{DOMAIN}.{devicename}")

#--------------------------------------------------------------------
    def _format_fname_devtype(self, devicename):
        return (f"{self.fname.get(devicename)} ({self.device_type.get(devicename)})")

#--------------------------------------------------------------------
    def _format_fname_devicename(self, devicename):
        return (f"{self.fname.get(devicename)} ({devicename})")

#--------------------------------------------------------------------
    def _format_fname_zone(self, zone):
        return (f"{self.zone_fname.get(zone)}")

#--------------------------------------------------------------------
    def _format_devicename_zone(self, devicename, zone = None):
        if zone is None:
            zone = self.base_zone
        return (f"{devicename}:{zone}")
#--------------------------------------------------------------------
    def _trace_device_attributes(self, devicename, description,
            fct_name, attrs):

        try:
            #Extract only attrs needed to update the device
            if attrs == None:
                return

            attrs_in_attrs = {}
            #if 'iCloud' in description:
            if (instr(description, "iCloud") or instr(description, "FamShr")):
                attrs_base_elements = TRACE_ICLOUD_ATTRS_BASE
                if ATTR_LOCATION in attrs:
                    attrs_in_attrs  = attrs[ATTR_LOCATION]
            elif 'Zone' in description:
                attrs_base_elements = attrs
            else:
                attrs_base_elements = TRACE_ATTRS_BASE
                if ATTR_ATTRIBUTES in attrs:
                    attrs_in_attrs  = attrs[ATTR_ATTRIBUTES]

            trace_attrs = {k: v for k, v in attrs.items() \
                                       if k in attrs_base_elements}

            trace_attrs_in_attrs = {k: v for k, v in attrs_in_attrs.items() \
                                       if k in attrs_base_elements}

            #trace_attrs = attrs

            ls = self.state_last_poll.get(devicename)
            cs = self.state_this_poll.get(devicename)
            log_msg = (f"_ {description} Attrs ___ ({fct_name})")
            self.log_debug_msg(devicename, log_msg)

            log_msg = (f"{description} Last State-{ls}, This State-{cs}")
            self.log_debug_msg(devicename, log_msg)

            log_msg = (f"{description} Attrs-{trace_attrs}{trace_attrs_in_attrs}")
            self.log_debug_msg(devicename, log_msg)


        except Exception as err:
            pass
            #_LOGGER.exception(err)

        return

#--------------------------------------------------------------------
    def _notify_device(self, message, devicename = None):
        return
        for devicename_x in self.tracked_devices:
            if devicename and devicename_x != devicename:
                continue

            entity_id    = (f"ios_{devicename_x}")
            msg = (f"'{message}'")
            service_data = {"message": "test message"}

            #_LOGGER.warning(service_data_q)
            #_LOGGER.warning(service_data)
            self.hass.services.call("notify", entity_id, service_data)

#--------------------------------------------------------------------
    def _get_iosappv2_device_sensor_trigger(self, devicename):

        entity_id = (f"sensor.{self.iosapp_v2_last_trigger_entity.get(devicename)}")

        try:
            if self.iosapp_version.get(devicename) == 2:
                trigger = self.hass.states.get(entity_id).state
                trigger_time, trigger_time_secs, trigger_timestamp = \
                        self._get_entity_last_changed_time(entity_id)

                trigger = IOS_TRIGGER_ABBREVIATIONS.get(trigger, trigger)

                return trigger, trigger_time, trigger_time_secs

            else:
                return '', '', 0

        except Exception as err:
            _LOGGER.exception(err)
            return '', '', 0

#########################################################
#
#   DEVICE ZONE ROUTINES
#
#########################################################
    def _get_zone(self, devicename, latitude, longitude):

        '''
        Get current zone of the device based on the location """

        This is the same code as (active_zone/async_active_zone) in zone.py
        but inserted here to use zone table loaded at startup rather than
        calling hass on all polls
        '''
        zone_selected_dist = HIGH_INTEGER
        zone_selected      = None

        log_msg = f"Select Zone > "
        for zone in self.zone_lat:
            #Skip another device's stationary zone
            if instr(zone, 'stationary') and instr(zone, devicename) == False:
                continue

            zone_dist = self._calc_distance_km(latitude, longitude,
                self.zone_lat.get(zone), self.zone_long.get(zone))

            in_zone      = zone_dist <= self.zone_radius_km.get(zone)
            closer_zone  = zone_selected is None or zone_dist <= zone_selected_dist
            smaller_zone = (zone_dist == zone_selected_dist and
                    self.zone_radius_km.get(zone) < self.zone_radius_km.get(zone_selected))

            if in_zone and (closer_zone or smaller_zone):
                zone_selected_dist  = round(zone_dist, 2)
                zone_selected       = zone

            log_msg += (f"{self.zone_fname.get(zone)}-"
                        f"{self._format_dist(zone_dist)}/r"
                        f"{round(self.zone_radius_m.get(zone))}, ")

        log_msg = (f"{log_msg[:-2]} > Selected-{self.zone_fname.get(zone_selected, AWAY)}")
        self.log_debug_msg(devicename, log_msg)
        self._save_event(devicename, log_msg)

        if zone_selected is None:
            zone_selected      = NOT_HOME
            zone_selected_dist = 0

        elif instr(zone,'nearzone'):
            zone_selected = 'near_zone'


        #If the zone changed from a previous poll, save it and set the new one
        if (self.zone_current.get(devicename) != zone_selected):
            self.zone_last[devicename] = self.zone_current.get(devicename)

            #First time thru, initialize zone_last
            if (self.zone_last.get(devicename) == ''):
                self.zone_last[devicename]  = zone_selected

            self.zone_current[devicename]   = zone_selected
            self.zone_timestamp[devicename] = \
                        dt_util.now().strftime(self.um_date_time_strfmt)

        log_msg = (f"►GET CURRENT ZONE END, Zone-{zone_selected}, "
                   f"{format_gps(latitude, longitude)}, "
                   f"StateThisPoll-{self.state_this_poll.get(devicename)}, "
                   f"LastZone-{self.zone_last.get(devicename)}, "
                   f"ThisZone-{self.zone_current.get(devicename)}")
        self.log_debug_msg(devicename, log_msg)

        return zone_selected

#--------------------------------------------------------------------
    @staticmethod
    def _get_zone_names(zone_name):
        """
        Make zone_names 1, 2, & 3 out of the zone_name value for sensors

        name1 = home --> Home
                not_home --> Away
                gary_iphone_stationary --> Stationary
        name2 = gary_iphone_stationary --> Gary Iphone Stationary
                office_bldg_1 --> Office Bldg 1
        name3 = gary_iphone_stationary --> GaryIphoneStationary
                office__bldg_1 --> Office Bldg1
        """
        if zone_name:
            if STATIONARY in zone_name:
                name1 = STATIONARY
            elif NOT_HOME in zone_name:
                name1 = AWAY
            else:
                name1 = zone_name.title()

            if zone_name == ATTR_ZONE:
                badge_state = name1

            name2 = zone_name.title().replace('_', ' ', 99)
            name3 = zone_name.title().replace('_', '', 99)
        else:
            name1 = NOT_SET
            name2 = 'Not Set'
            name3 = 'NotSet'

        return [zone_name, name1, name2, name3]

#--------------------------------------------------------------------
    @staticmethod
    def _format_zone_name(devicename, zone):
        '''
        The Stationary zone info is kept by 'devicename_stationary'. Other zones
        are kept as 'zone'. Format the name based on the zone.
        '''
        return f"{devicename}_stationary" if zone == STATIONARY else zone

#--------------------------------------------------------------------
    def _set_base_zone_name_lat_long_radius(self, zone):
        '''
        Set the base_zone's name, lat, long & radius
        '''
        self.base_zone        = zone
        self.base_zone_name   = self.zone_fname.get(zone)
        self.base_zone_lat    = self.zone_lat.get(zone)
        self.base_zone_long   = self.zone_long.get(zone)
        self.base_zone_radius_km = float(self.zone_radius_km.get(zone))

        return

#--------------------------------------------------------------------
    def _zone_distance_m(self, devicename, zone, latitude, longitude):
        '''
        Get the distance from zone `zone`
        '''

        zone_dist = HIGH_INTEGER

        if self.zone_lat.get(zone):
            zone_name = self._format_zone_name(devicename, zone)

            zone_dist = self._calc_distance_m(
                            latitude,
                            longitude,
                            self.zone_lat.get(zone_name),
                            self.zone_long.get(zone_name))

            log_msg = (f"INZONE 1KM CHECK {devicename}, Zone-{zone_name}, "
                       f"CurrGPS-{format_gps(latitude, longitude)}, "
                       f"ZoneGPS-{format_gps(self.zone_lat.get(zone_name), self.zone_long.get(zone_name))}, "
                       f"Dist-{zone_dist} m")
            self.log_debug_msg(devicename, log_msg)

        return zone_dist

#--------------------------------------------------------------------
    def _is_inzone(self, devicename):
        return (self.state_this_poll.get(devicename) != NOT_HOME)

    def _isnot_inzone(self, devicename):
        return (self.state_this_poll.get(devicename) == NOT_HOME)

    def _was_inzone(self, devicename):
        return (self.state_last_poll.get(devicename) != NOT_HOME)

    def _wasnot_inzone(self, devicename):
        return (self.state_last_poll.get(devicename) == NOT_HOME)

    @staticmethod
    def _is_inzoneZ(zone):
        return (zone != NOT_HOME)

    @staticmethod
    def _isnot_inzoneZ(zone):
        #_LOGGER.warning("_isnot_inzoneZ = %s",(zone == NOT_HOME))
        return (zone == NOT_HOME)
#--------------------------------------------------------------------
    def _wait_if_update_in_process(self, devicename=None):
        #An update is in process, must wait until done
        wait_cnt = 0
        while self.update_in_process_flag:
            wait_cnt += 1
            if devicename:
                attrs = {}
                attrs[ATTR_INTERVAL] = (f"►WAIT-{wait_cnt}")

                self._update_device_sensors(devicename, attrs)

            time.sleep(2)

#--------------------------------------------------------------------
    def _update_last_latitude_longitude(self, devicename, latitude, longitude, line_no=0):
        #Make sure that the last latitude/longitude is not set to the
        #base stationary one before updating. If it is, do not save them

        if latitude == None or longitude == None:
            error_msg = (f"Discarded > Undefined GPS Coordinates "
                         f"(line {line_no})")

        elif latitude == self.stat_zone_base_lat and longitude == self.stat_zone_base_long:
            error_msg = (f"Discarded > Can not set current location to Stationary "
                         f"Base Zone location {format_gps(latitude, longitude)} "
                         f"(line {line_no})")
        else:
            self.last_lat[devicename]  = latitude
            self.last_long[devicename] = longitude
            return True

        self._save_event_halog_info(devicename, error_msg)
        return False

#--------------------------------------------------------------------
    @staticmethod
    def _latitude_longitude_none(latitude, longitude):
        return (latitude == None or longitude == None)

#--------------------------------------------------------------------
    def _update_stationary_zone(self, devicename,
                latitude, longitude, visible_flag=False):
        """ Create/update dynamic stationary zone """

        try:
            event_log_devicename = "*" if self.start_icloud3_inprocess_flag else devicename
            stat_zone_name = self._format_zone_name(devicename, STATIONARY)

            #Make sure stationary zone is not being moved to another zone's location.
            for zone in self.zone_lat:
                if instr(zone, STATIONARY) == False:
                    zone_dist = self._calc_distance_m(latitude, longitude,
                        self.zone_lat.get(zone), self.zone_long.get(zone))
                    if zone_dist < (self.stat_zone_radius_m + self.zone_radius_m.get(zone)):
                        return False

            attrs = {}
            attrs[CONF_NAME]      = stat_zone_name
            attrs[ATTR_LATITUDE]  = latitude
            attrs[ATTR_LONGITUDE] = longitude
            attrs[ATTR_RADIUS]    = self.stat_zone_radius_m
            attrs['passive']      = False
            attrs['icon']         = (f"mdi:{self.stat_zone_devicename_icon.get(devicename)}")
            attrs[ATTR_FRIENDLY_NAME] = STATIONARY

            #If Stationary zone is hidden, don't hide it but reduce the size
            if visible_flag == STATIONARY_ZONE_HIDDEN:
                attrs[ATTR_RADIUS] = 3

            self.log_debug_msg(devicename, f"Set Stat Zone-{attrs}")

            zone_dist = self._calc_distance_m(latitude, longitude,
                    self.zone_lat.get(stat_zone_name), self.zone_long.get(stat_zone_name))
            zone_dist_msg = f"{zone_dist} m" if zone_dist < 500 else f"{round(zone_dist/1000, 2)} km"

            self.zone_lat[stat_zone_name]       = latitude
            self.zone_long[stat_zone_name]      = longitude
            self.zone_radius_km[stat_zone_name] = self.stat_zone_radius_km
            self.zone_radius_m[stat_zone_name]  = self.stat_zone_radius_m
            self.zone_passive[stat_zone_name]   = not visible_flag

            self.hass.states.set("zone." + stat_zone_name, "zoning", attrs)

            self._trace_device_attributes(
                    stat_zone_name, "CreateStatZone", "CreateStatZone", attrs)

            event_msg = (f"Set Stationary Zone > {stat_zone_name}, "
                         f"GPS-{format_gps(latitude, longitude)}, "
                         f"DistFromLastLoc-{zone_dist_msg}")
            self._save_event_halog_info(event_log_devicename, event_msg)

            return True

        except Exception as err:
            _LOGGER.exception(err)
            log_msg = (f"►►INTERNAL ERROR (UpdtStatZone-{err})")
            self.log_error_msg(log_msg)

            return False
#--------------------------------------------------------------------
    def _update_device_sensors(self, arg_devicename, attrs:dict):
        '''
        Update/Create sensor for the device attributes

        sensor_device_attrs = ['distance', 'calc_distance', 'waze_distance',
                          'travel_time', 'dir_of_travel', 'interval', 'info',
                          'last_located', 'last_update', 'next_update',
                          'poll_count', 'trigger', 'battery', 'battery_state',
                          'gps_accuracy', 'zone', 'last_zone', 'travel_distance']

        sensor_attrs_format = {'distance': 'dist', 'calc_distance': 'dist',
                          'travel_distance': 'dist', 'battery': '%',
                          'dir_of_travel': 'title'}
        '''
        try:
            if not attrs:
                return

            #check to see if arg_devicename is really devicename_zone
            #if arg_devicename.find(':') == -1:
            if instr(arg_devicename, ":") == False:
                devicename  = arg_devicename
                prefix_zone = self.base_zone
            else:
                devicename  = arg_devicename.split(':')[0]
                prefix_zone = arg_devicename.split(':')[1]

            badge_state = None
            badge_zone  = None
            badge_dist  = None
            base_entity = self.sensor_prefix_name.get(devicename)

            if prefix_zone == HOME:
                base_entity = (f"sensor.{self.sensor_prefix_name.get(devicename)}")
                attr_fname_prefix = self.sensor_attr_fname_prefix.get(devicename)
            else:
                base_entity = (f"sensor.{prefix_zone}_{self.sensor_prefix_name.get(devicename)}")
                attr_fname_prefix = (f"{prefix_zone.replace('_', ' ', 99).title()}_"
                                     f"{self.sensor_attr_fname_prefix.get(devicename)}")

            for attr_name in SENSOR_DEVICE_ATTRS:
                sensor_entity = (f"{base_entity}_{attr_name}")
                if attr_name in attrs:
                    state_value = attrs.get(attr_name)
                else:
                    continue

                sensor_attrs = {}
                if attr_name in SENSOR_ATTR_FORMAT:
                    format_type = SENSOR_ATTR_FORMAT.get(attr_name)
                    if format_type == "dist":
                        sensor_attrs['unit_of_measurement'] = \
                                self.unit_of_measurement
                        #state_value = round(state_value, 2) if state_value else 0.00

                    elif format_type == "diststr":
                        try:
                            x = (state_value / 2)
                            sensor_attrs['unit_of_measurement'] = \
                                self.unit_of_measurement
                        except:
                            sensor_attrs['unit_of_measurement'] = ''
                    elif format_type == "%":
                        sensor_attrs['unit_of_measurment'] = '%'
                    elif format_type == 'title':
                        state_value = state_value.title().replace('_', ' ')
                    elif format_type == 'kph-mph':
                        sensor_attrs['unit_of_measurement'] = self.um_kph_mph
                    elif format_type == 'm-ft':
                        sensor_attrs['unit_of_measurement'] = self.um_m_ft

                if attr_name in SENSOR_ATTR_ICON:
                    sensor_attrs['icon'] = SENSOR_ATTR_ICON.get(attr_name)

                if attr_name in SENSOR_ATTR_FNAME:
                    sensor_attrs[ATTR_FRIENDLY_NAME] = (f"{attr_fname_prefix}{SENSOR_ATTR_FNAME.get(attr_name)}")

                self._update_device_sensors_hass(devicename, base_entity, attr_name,
                                    state_value, sensor_attrs)

                if attr_name == 'zone':
                    zone_names = self._get_zone_names(state_value)
                    if badge_state == None:
                        badge_state = zone_names[1]
                    self._update_device_sensors_hass(devicename, base_entity,
                                "zone_name1", zone_names[1], sensor_attrs)

                    self._update_device_sensors_hass(devicename, base_entity,
                                "zone_name2", zone_names[2], sensor_attrs)

                    self._update_device_sensors_hass(devicename, base_entity,
                                "zone_name3", zone_names[3], sensor_attrs)

                elif attr_name == 'last_zone':
                    zone_names = self._get_zone_names(state_value)

                    self._update_device_sensors_hass(devicename, base_entity,
                                "last_zone_name1", zone_names[1], sensor_attrs)

                    self._update_device_sensors_hass(devicename, base_entity,
                                "last_zone_name2", zone_names[2], sensor_attrs)

                    self._update_device_sensors_hass(devicename, base_entity,
                                "last_zone_name3", zone_names[3], sensor_attrs)

                elif attr_name == 'zone_distance':
                    if state_value and float(state_value) > 0:
                        badge_state = (f"{state_value} {self.unit_of_measurement}")

            if badge_state:
                self._update_device_sensors_hass(devicename,
                            base_entity,
                            "badge",
                            badge_state,
                            self.sensor_badge_attrs.get(devicename))
                #log_msg=(f"Badge -{badge_entity}, state_value-{badge_state} "
                #         f"{self.sensor_badge_attrs.get(devicename)}")
                #self.log_debug_msg(devicename, log_msg)
            return True

        except Exception as err:
            _LOGGER.exception(err)
            log_msg = (f"►►INTERNAL ERROR (UpdtSensorUpdate-{err})")
            self.log_error_msg(log_msg)

            return False
#--------------------------------------------------------------------
    def _update_device_sensors_hass(self, devicename, base_entity, attr_name,
                                    state_value, sensor_attrs):

        try:
            state_value = state_value[0:250]
        except:
            pass

        if attr_name in self.sensors_custom_list:
            sensor_entity = (f"{base_entity}_{attr_name}")

            self.hass.states.set(sensor_entity, state_value, sensor_attrs)

#--------------------------------------------------------------------
    def _format_info_attr(self, devicename, battery,
                            gps_accuracy, dist_last_poll_moved_km,
                            zone, location_isold_flag, location_time_secs):  #location_time):

        """
        Initialize info attribute
        """
        devicename_zone = self._format_devicename_zone(devicename)
        try:
            info_msg = ''
            if self.info_notification != '':
                info_msg = f"●●{self.info_notification}●●"
                self.info_notification = ''

            if self.base_zone != HOME:
                info_msg += (f" • Base.Zone: {self.base_zone_name}")

            if (self.TRK_METHOD_IOSAPP and
                    self.tracking_method_config != IOSAPP):
                info_msg += (f" • Track.Method: {self.trk_method_short_name}")

            if self.overrideinterval_seconds.get(devicename) > 0:
                info_msg += " • Overriding.Interval"

            if zone == 'near_zone':
                info_msg += " • NearZone"

            if battery > 0:
                info_msg += f" • Battery-{battery}%"

            if gps_accuracy > self.gps_accuracy_threshold:
                info_msg += (f" • Poor.GPS.Accuracy, Dist-{self._format_dist(gps_accuracy)}")
                if self.old_loc_poor_gps_cnt.get(devicename) > 0:
                    info_msg += (f" (#{self.old_loc_poor_gps_cnt.get(devicename)})")
                if (self._is_inzoneZ(zone) and
                        self.ignore_gps_accuracy_inzone_flag):
                    info_msg += "-Ignored"

            isold_cnt = self.old_loc_poor_gps_cnt.get(devicename)

            if isold_cnt > 0:
                age = self._secs_since(self.last_located_secs.get(devicename))
                info_msg += (f" • Old.Location, Age-{self._secs_to_time_str(age)} (#{isold_cnt})")

            if self.waze_data_copied_from.get(devicename) is not None:
                copied_from = self.waze_data_copied_from.get(devicename)
                if devicename != copied_from:
                    info_msg += (f" • Using Waze data from {self.fname.get(copied_from)}")

            #usage_count_msg, usage_count = self._display_usage_counts(devicename, force_display=True)
            #if usage_count_msg:
            #     info_msg += (f" ●{usage_count_msg}")

        except Exception as err:
            _LOGGER.exception(err)
            info_msg += (f"Error setting up info attribute-{err}")
            self.log_error_msg(info_msg)

        return info_msg

#--------------------------------------------------------------------
    def _display_info_status_msg(self, devicename_zone, info_msg):
        '''
        Display a status message in the info sensor. If the devicename_zone
        parameter contains the base one (devicename:zone), display only for that
        devicename_one, otherwise (devicename), display for all zones for
        the devicename.
        '''
        try:
            save_base_zone = self.base_zone

            #if devicename_zone.find(':') >= 0:
            if instr(devicename_zone, ':'):
                devicename = devicename_zone.split(':')[0]
                devicename_zone_list = [devicename_zone.split(':')[1]]
            else:
                devicename = devicename_zone
                devicename_zone_list = self.track_from_zone.get(devicename)

            for zone in devicename_zone_list:
                self.base_zone = zone
                attrs = {}
                attrs[ATTR_INFO] = f"●{info_msg}●"
                self._update_device_sensors(devicename, attrs)

        except:
            pass

        self.base_zone = save_base_zone

#--------------------------------------------------------------------
    def _update_count_update_ignore_attribute(self, devicename, info = None):
        self.count_update_ignore[devicename] += 1

        try:
            attrs  = {}
            attrs[ATTR_POLL_COUNT] = self._format_poll_count(devicename)

            self._update_device_sensors(devicename, attrs)

        except:
            pass
#--------------------------------------------------------------------
    def _format_poll_count(self, devicename):

        return (f"{self.count_update_icloud.get(devicename)}:"
                f"{self.count_update_iosapp.get(devicename)}:"
                f"{self.count_update_ignore.get(devicename)}")

#--------------------------------------------------------------------
    def _display_usage_counts(self, devicename, force_display=False):

        try:
            total_count = self.count_update_icloud.get(devicename) + \
                          self.count_update_iosapp.get(devicename) + \
                          self.count_update_ignore.get(devicename) + \
                          self.count_state_changed.get(devicename) + \
                          self.count_trigger_changed.get(devicename) + \
                          self.count_request_iosapp_locate.get(devicename)


            pyi_avg_time_per_call = self.time_pyicloud_calls / \
                    (self.count_pyicloud_authentications + self.count_pyicloud_location_update) \
                        if self.count_pyicloud_location_update > 0 else 0
            #If updating the devicename's info_msg, only add to the event log
            #and info_msg if the counter total is divisible by 5.
            total_count = 1
            hour = int(dt_util.now().strftime('%H'))
            if force_display:
                pass
            elif (hour % 3) != 0:
                return (None, 0)
            elif total_count == 0:
                return (None, 0)

            #    ¤s=<table>                     Table start, Row start
            #    ¤e=</table>                   Row end, Table end
            #    §=</tr><tr>                        Row end, next row start
            #    «40=<tr><td style='width: 40%'>        Col start, 40% width
            #    »=</td></tr>
            #    ¦0=</td><td>                       Col end, next col start
            #    ¦10=</td><td style='width: 10%'>   Col end, next col start-width 10%
            #    ¦40=</td><td style='width: 40%'>   Col end, next col start-width 40%

            count_msg =  (f"¤s")
            state_trig_count = self.count_state_changed.get(devicename) + self.count_trigger_changed.get(devicename)
            if self.TRK_METHOD_FMF_FAMSHR:
                column_right_hdr_text = "iCloud.Totals"
                count_msg += (f"«35State/Trigger Chgs¦15{state_trig_count}¦30Authentications¦20{self.count_pyicloud_authentications}»"
                              f"«35iCloud Updates¦15{self.count_update_icloud.get(devicename)}¦30Web Svc Locates¦20{self.count_pyicloud_location_update}»"
                              f"«35iOS App Updates¦15{self.count_update_iosapp.get(devicename)}¦30Time/Locate¦20{round(pyi_avg_time_per_call, 2)} secs»")
            else:
                column_right_hdr_text = "iOSApp.Totals"
                count_msg += (f"«35State/Triggers Chgs¦15{state_trig_count}¦30iOS Locate Rqsts¦20{self.count_request_iosapp_locate.get(devicename)}»"
                              f"«35iCloud Updates¦15{self.count_update_icloud.get(devicename)}¦30iOS App Updates ¦20{self.count_update_iosapp.get(devicename)}»")

            count_msg += (f"«35Discarded¦15{self.count_update_ignore.get(devicename)}¦30Waze Routes¦20{self.count_waze_locates.get(devicename)}»"
                          f"¤e")

            self._save_event(devicename, f"{EVLOG_COLOR_STATS}{count_msg}",
                        column_left_hdr="Device.Totals", column_right_hdr=column_right_hdr_text)

        except Exception as err:
            _LOGGER.exception(err)

        return (None, 0)

#########################################################
#
#   Perform tasks on a regular time schedule
#
#########################################################
    def _timer_tasks_every_hour(self):
        for devicename in self.tracked_devices:
            self._display_usage_counts(devicename)

#--------------------------------------------------------------------
    def _timer_tasks_midnight(self):
        for devicename in self.tracked_devices:
            devicename_zone = self._format_devicename_zone(devicename, HOME)

            event_msg = (f"^^^ iCloud3 v{VERSION} Daily Summary >"
                         f"{dt_util.now().strftime('%A, %b %d')}")
            self._save_event_halog_info(devicename, event_msg)

            event_msg = (f"Tracking Devices > {self.track_devicename_list}")
            self._save_event_halog_info(devicename, event_msg)

            if self.iosapp_version.get(devicename) == 1:
                event_msg = (f"IOS App v1 monitoring > device_tracker.{devicename}")
                self._save_event_halog_info(devicename, event_msg)

            elif self.iosapp_version.get(devicename) == 2:
                event_msg = (f"IOS App v2 monitoring > "
                             f"device_tracker.{self.devicename_iosapp.get(devicename)}, "
                             f"sensor.{self.iosapp_v2_last_trigger_entity.get(devicename)}")
                self._save_event_halog_info(devicename, event_msg)

            self.count_pyicloud_authentications = 0
            self.count_pyicloud_location_update = 0
            self.time_pyicloud_calls            = 0.0
            #self.event_cnt[devicename]          = 0
            self._initialize_usage_counters(devicename, True)

        for devicename_zone in self.waze_distance_history:
            self.waze_distance_history[devicename_zone] = ''

        self.icloud_authenticate_account()

#--------------------------------------------------------------------
    def _timer_tasks_1am(self):
        self._calculate_time_zone_offset()

#########################################################
#
#   VARIABLE DEFINITION & INITIALIZATION FUNCTIONS
#
#########################################################
    def _define_tracking_control_fields(self):
        self.icloud3_started_secs            = 0
        self.icloud_acct_auth_error_cnt      = 0
        self.immediate_retry_flag            = False
        self.time_zone_offset_seconds        = self._calculate_time_zone_offset()
        self.setinterval_cmd_devicename      = None
        self.update_in_process_flag          = False
        self.track_devicename_list           = ''
        self.any_device_being_updated_flag   = False
        #self.tracked_devices             = {}
        self.tracked_devices_config_parm     = {} #config file item for devicename
        self.tracked_devices                 = []

        self.trigger                         = {}    #device update trigger
        self.last_iosapp_trigger             = {}    #last trigger issued by iosapp
        self.got_exit_trigger_flag           = {}    #iosapp issued exit trigger leaving zone
        self.device_being_updated_flag       = {}
        self.device_being_updated_retry_cnt  = {}
        self.last_v2_state                   = {}
        self.last_v2_state_changed_time      = {}
        self.last_v2_state_changed_secs      = {}
        self.last_v2_trigger                 = {}
        self.last_v2_trigger_changed_time    = {}
        self.last_v2_trigger_changed_secs    = {}

        self.iosapp_update_flag              = {}
        self.iosapp_version                  = {}
        self.iosapp_v2_last_trigger_entity   = {} #sensor entity extracted from entity_registry
        self.iosapp_location_update_secs     = {}
        self.iosapp_stat_zone_action_msg_cnt = {}
        self.authenticated_time              = 0
        self.info_notification               = ''

        this_update_time = dt_util.now().strftime('%H:%M:%S')
#--------------------------------------------------------------------
    def _define_event_log_fields(self):
        #self.event_cnt                   = {}
        self.event_log_table             = []
        self.event_log_base_attrs        = ''
        self.log_table_max_items         = 999
        self.event_log_clear_secs        = HIGH_INTEGER
        self.event_log_sensor_state      = ''
        self.event_log_last_devicename   = '*'

#--------------------------------------------------------------------
    def _define_device_fields(self):
        '''
        Dictionary fields for each devicename
        '''
        self.fname                    = {}    #name made from status[CONF_NAME]
        self.badge_picture            = {}    #devicename picture from badge setup
        self.api_devices              = None  #icloud.api.devices obj
        self.api_device_devicename    = {}    #icloud.api.device obj for each devicename
        self.data_source              = {}
        self.device_type              = {}
        self.iosapp_version1_flag     = {}
        self.devicename_iosapp        = {}
        self.devicename_iosapp_id     = {}
        self.notify_iosapp_entity     = {}
        self.devicename_verified      = {}    #Set to True in mode setup fcts
        self.fmf_id                   = {}
        self.fmf_devicename_email     = {}
        self.seen_this_device_flag    = {}
        self.device_tracker_entity    = {}
        self.device_tracker_entity_iosapp = {}
        self.track_from_zone          = {}    #Track device from other zone

#--------------------------------------------------------------------
    def _define_device_status_fields(self):
        '''
        Dictionary fields for each devicename
        '''
        self.tracking_device_flag            = {}

        self.state_this_poll                 = {}
        self.state_last_poll                 = {}
        self.zone_last                       = {}
        self.zone_current                    = {}
        self.zone_timestamp                  = {}
        self.state_change_flag               = {}

        self.location_data                   = {}
        self.overrideinterval_seconds        = {}
        self.last_located_time               = {}
        self.last_located_secs               = {}    #device timestamp in seconds
        self.went_3km                        = {} #>3 km/mi, probably driving

#--------------------------------------------------------------------
    def _initialize_um_formats(self, unit_of_measurement):
        #Define variables, lists & tables
        if unit_of_measurement == 'mi':
            self.um_time_strfmt          = '%I:%M:%S'
            self.um_time_strfmt_ampm     = '%I:%M:%S%P'
            self.um_date_time_strfmt     = '%Y-%m-%d %I:%M:%S'
            self.um_km_mi_factor         = 0.62137
            self.um_m_ft                 = 'ft'
            self.um_kph_mph              = 'mph'
        else:
            self.um_time_strfmt          = '%H:%M:%S'
            self.um_time_strfmt_ampm     = '%H:%M:%S'
            self.um_date_time_strfmt     = '%Y-%m-%d %H:%M:%S'
            self.um_km_mi_factor         = 1
            self.um_m_ft                 = 'm'
            self.um_kph_mph              = 'kph'

#--------------------------------------------------------------------
    def _setup_tracking_method(self, tracking_method):
        '''
        tracking_method: method
        tracking_method: method, iosapp1

        tracking_method can have a secondary option to use iosappv1 even if iosv2 is
        on the devices
        '''

        trk_method_split     = (f"{tracking_method}_").split('_')
        trk_method_primary   = trk_method_split[0]
        trk_method_secondary = trk_method_split[1]

        self.TRK_METHOD_FMF        = (trk_method_primary == FMF)
        self.TRK_METHOD_FAMSHR     = (trk_method_primary == FAMSHR)
        self.TRK_METHOD_FMF_FAMSHR = (trk_method_primary in FMF_FAMSHR)
        if (self.TRK_METHOD_FMF_FAMSHR and PYICLOUD_IC3_IMPORT_SUCCESSFUL is False):
           trk_method_primary = IOSAPP

        self.TRK_METHOD_IOSAPP = (trk_method_primary in IOSAPP_IOSAPP1)

        self.trk_method_config     = trk_method_primary
        self.trk_method            = trk_method_primary
        self.trk_method_name       = TRK_METHOD_NAME.get(trk_method_primary)
        self.trk_method_short_name = TRK_METHOD_SHORT_NAME.get(trk_method_primary)

        if self.TRK_METHOD_FMF_FAMSHR and self.password == '':
            event_msg = ("iCloud3 Error > The password is required for the "
                f"{self.trk_method_short_name} tracking method. The "
                f"IOS App tracking_method will be used.")
            self._save_event_halog_error("*", event_msg)

            self._setup_iosapp_tracking_method()
#--------------------------------------------------------------------
    def _setup_iosapp_tracking_method(self):
        """ Change tracking method to IOSAPP if FMF or FAMSHR error """
        self.trk_method_short_name = TRK_METHOD_SHORT_NAME.get(IOSAPP)
        self.trk_method_config     = IOSAPP
        self.trk_method            = IOSAPP
        self.trk_method_name       = TRK_METHOD_NAME.get(IOSAPP)
        self.TRK_METHOD_IOSAPP     = True
        self.TRK_METHOD_FMF        = False
        self.TRK_METHOD_FAMSHR     = False
        self.TRK_METHOD_FMF_FAMSHR = False


#--------------------------------------------------------------------
    def _initialize_device_status_fields(self, devicename):
        '''
        Make domain name entity ids for the device_tracker and
        sensors for each device so we don't have to do it all the
        time. Then check to see if 'sensor.geocode_location'
        exists. If it does, then using iosapp version 2.

        examples of entity field results:
        device_tracker_entity = {'gary_iphone': 'device_tracker.gary_iphone'}
        device_tracker_entity_iosapp = {'gary_iphone': 'device_tracker.gary_iphone_mobapp'}
        iosapp_version = {'gary_iphone': 2}
        notify_iosapp_entity = {'gary_iphone': 'mobile_app_gary_iphone)'}
        '''
        self.device_tracker_entity[devicename] = (f"{DOMAIN}.{devicename}")
        self.device_tracker_entity_iosapp[devicename] = \
            (f"{DOMAIN}.{self.devicename_iosapp.get(devicename)}")
        self.notify_iosapp_entity[devicename] = \
            (f"{['', 'ios', 'mobile_app'][self.iosapp_version.get(devicename)]}_{devicename}")

        entity_id = self.device_tracker_entity.get(devicename)
        self.state_this_poll[devicename]              = self._get_state(entity_id)
        self.state_last_poll[devicename]              = NOT_SET
        self.zone_last[devicename]                    = ''
        self.zone_current[devicename]                 = ''
        self.zone_timestamp[devicename]               = ''
        self.state_change_flag[devicename]            = False
        self.trigger[devicename]                      = 'iCloud3'
        self.last_iosapp_trigger[devicename]          = ''
        self.got_exit_trigger_flag[devicename]        = False
        self.last_located_time[devicename]            = HHMMSS_ZERO
        self.last_located_secs[devicename]            = 0
        self.location_data[devicename]                = INITIAL_LOCATION_DATA
        self.went_3km[devicename]                     = False
        self.iosapp_update_flag[devicename]           = False
        self.seen_this_device_flag[devicename]        = False
        self.device_being_updated_flag[devicename]    = False
        self.device_being_updated_retry_cnt[devicename] = 0
        self.iosapp_location_update_secs[devicename]  = 0

        #if devicename not in self.sensor_prefix_name:
        self.sensor_prefix_name[devicename] = devicename

        #iosapp v2 entity info
        self.last_v2_state[devicename]                = ''
        self.last_v2_state_changed_time[devicename]   = ''
        self.last_v2_state_changed_secs[devicename]   = 0
        self.last_v2_trigger[devicename]              = ''
        self.last_v2_trigger_changed_time[devicename] = ''
        self.last_v2_trigger_changed_secs[devicename] = 0

#--------------------------------------------------------------------
    def _define_device_tracking_fields(self):
        #times, flags
        self.update_timer             = {}
        self.overrideinterval_seconds = {}
        self.dist_from_zone_km_small_move_total = {}
        self.this_update_secs         = 0

        #location, gps
        self.old_loc_poor_gps_cnt     = {}    # override interval while < 4
        self.old_loc_poor_gps_msg     = {}
        self.old_location_secs        = {}

        self.poor_gps_accuracy_flag   = {}
        self.last_long                = {}
        self.last_battery             = {}   #used to detect iosapp v2 change
        self.last_lat                 = {}
        self.last_gps_accuracy        = {}   #used to detect iosapp v2 change

#--------------------------------------------------------------------
    def _initialize_device_tracking_fields(self, devicename):
        #times, flags
        self.update_timer[devicename]           = time.time()
        self.overrideinterval_seconds[devicename] = 0
        self.dist_from_zone_km_small_move_total[devicename] = 0

        #location, gps
        self.old_loc_poor_gps_cnt[devicename]   = 0
        self.old_loc_poor_gps_msg[devicename]   = False
        self.old_location_secs[devicename]      = 90    #Timer (secs) before a location is old
        self.last_lat[devicename]               = self.zone_home_lat
        self.last_long[devicename]              = self.zone_home_long
        self.poor_gps_accuracy_flag[devicename] = False
        self.last_battery[devicename]           = 0
        self.last_gps_accuracy[devicename]      = 0

        #self.event_cnt[devicename]              = 0

        #Other items
        self.data_source[devicename]            = ''
        self.last_iosapp_msg[devicename]        = ''
        self.iosapp_stat_zone_action_msg_cnt[devicename]= 0

#--------------------------------------------------------------------
    def _define_usage_counters(self):
        self.count_update_iosapp            = {}
        self.count_update_ignore            = {}
        self.count_update_icloud            = {}
        self.count_state_changed            = {}
        self.count_trigger_changed          = {}
        self.count_waze_locates             = {}
        self.time_waze_calls                = {}
        self.count_request_iosapp_locate    = {}
        self.count_pyicloud_authentications = 0
        self.count_pyicloud_location_update = 0
        self.time_pyicloud_calls            = 0.0

#--------------------------------------------------------------------
    def _initialize_usage_counters(self, devicename, clear_counters=True):
        if devicename not in self.count_update_iosapp or clear_counters:
            self.count_update_iosapp[devicename]   = 0
            self.count_update_ignore[devicename]   = 0
            self.count_update_icloud[devicename]   = 0
            self.count_state_changed[devicename]   = 0
            self.count_trigger_changed[devicename] = 0
            self.count_waze_locates[devicename]    = 0
            self.time_waze_calls[devicename]       = 0.0
            self.count_request_iosapp_locate[devicename] = 0



#--------------------------------------------------------------------
    def _initialize_next_update_time(self, devicename):
        for zone in self.track_from_zone.get(devicename):
            devicename_zone = self._format_devicename_zone(devicename, zone)

            self.next_update_time[devicename_zone] = HHMMSS_ZERO
            self.next_update_secs[devicename_zone] = 0

#--------------------------------------------------------------------
    def _define_sensor_fields(self, initial_load_flag):
        #Prepare sensors and base attributes

        if initial_load_flag:
            self.sensor_devicenames       = []
            self.sensors_custom_list      = []
            self.sensor_badge_attrs       = {}
            self.sensor_prefix_name       = {}
            self.sensor_attr_fname_prefix = {}

#--------------------------------------------------------------------
    def _define_device_zone_fields(self):
        '''
        Dictionary fields for each devicename_zone
        '''
        self.last_tavel_time        = {}
        self.interval_seconds       = {}
        self.interval_str           = {}
        self.last_distance_str      = {}
        self.last_update_time       = {}
        self.last_update_secs       = {}
        self.next_update_secs       = {}
        self.next_update_time       = {}
        self.next_update_in_secs    = {}
        self.next_update_devicenames= []

        #used to calculate distance traveled since last poll
        self.waze_time              = {}
        self.waze_dist              = {}
        self.calc_dist              = {}
        self.zone_dist              = {}

        self.last_dev_timestamp_ses = {}
        #self.old_loc_poor_gps_cnt   = {}

#--------------------------------------------------------------------
    def _initialize_device_zone_fields(self, devicename):
        #interval, distances, times

        for zone in self.track_from_zone.get(devicename):
            devicename_zone = self._format_devicename_zone(devicename, zone)

            self.last_tavel_time[devicename_zone]   = ''
            self.interval_seconds[devicename_zone]  = 0
            self.interval_str[devicename_zone]      = '0 sec'
            self.last_distance_str[devicename_zone] = ''
            self.last_update_time[devicename_zone]  = HHMMSS_ZERO
            self.last_update_secs[devicename_zone]  = 0
            self.next_update_time[devicename_zone]  = HHMMSS_ZERO
            self.next_update_secs[devicename_zone]  = 0
            self.next_update_in_secs[devicename_zone] = 0

            self.waze_history_data_used_flag[devicename_zone] = False
            self.waze_time[devicename_zone]         = 0
            self.waze_dist[devicename_zone]         = 0
            self.calc_dist[devicename_zone]         = 0
            self.zone_dist[devicename_zone]         = 0

        try:
            #set up stationary zone icon for devicename
            first_initial = self.fname.get(devicename)[0].lower()

            if devicename in self.stat_zone_devicename_icon:
                icon = self.stat_zone_devicename_icon.get(devicename)
            elif (f"alpha-{first_initial}-box") not in self.stat_zone_devicename_icon:
                icon_name = (f"alpha-{first_initial}-box")
            elif (f"alpha-{first_initial}-circle") not in self.stat_zone_devicename_icon:
                icon_name = (f"alpha-{first_initial}-circle")
            elif (f"alpha-{first_initial}-box-outline") not in self.stat_zone_devicename_icon:
                icon_name = (f"alpha-{first_initial}-box-outline")
            elif (f"alpha-{first_initial}-circle-outline") not in self.stat_zone_devicename_icon:
                icon_name = (f"alpha-{first_initial}-circle-outline")
            else:
                icon_name = (f"alpha-{first_initial}")

            self.stat_zone_devicename_icon[devicename] = icon_name
            self.stat_zone_devicename_icon[icon_name]  = devicename

            stat_zone_name = self._format_zone_name(devicename, STATIONARY)
            self.zone_fname[stat_zone_name] = "Stationary"

        except Exception as err:
            _LOGGER.exception(err)
            self.stat_zone_devicename_icon[devicename] = 'account'

#--------------------------------------------------------------------
    def _initialize_waze_fields(self, waze_region, waze_min_distance,
                waze_max_distance, waze_realtime):
        #Keep distance data to be used by another device if nearby. Also keep
        #source of copied data so that device won't reclone from the device
        #using it.
        self.waze_region   = waze_region
        self.waze_realtime = waze_realtime

        min_dist_msg = (f"{waze_min_distance} {self.unit_of_measurement}")
        max_dist_msg = (f"{waze_max_distance} {self.unit_of_measurement}")

        if self.unit_of_measurement == 'mi':
            self.waze_min_distance = self._mi_to_km(waze_min_distance)
            self.waze_max_distance = self._mi_to_km(waze_max_distance)
            min_dist_msg += (f" ({self.waze_min_distance} km)")
            max_dist_msg += (f" ({self.waze_max_distance} km)")
        else:
            self.waze_min_distance = float(waze_min_distance)
            self.waze_max_distance = float(waze_max_distance)

        self.waze_distance_history = {}
        self.waze_data_copied_from = {}
        self.waze_history_data_used_flag = {}

        self.waze_manual_pause_flag        = False  #If Paused vid iCloud command
        self.waze_close_to_zone_pause_flag = False  #pause if dist from zone < 1 flag

        if self.distance_method_waze_flag:
            log_msg = (f"Set Up Waze > Region-{self.waze_region}, "
                       f"MinDist-{min_dist_msg}, "
                       f"MaxDist-{max_dist_msg}, "
                       f"Realtime-{self.waze_realtime}")
            self.log_info_msg(log_msg)
            self._save_event("*", log_msg)

#--------------------------------------------------------------------
    def _initialize_attrs(self, devicename):
        attrs = {}
        attrs[ATTR_NAME]               = ''
        attrs[ATTR_ZONE]               = NOT_SET
        attrs[ATTR_LAST_ZONE]          = NOT_SET
        attrs[ATTR_ZONE_TIMESTAMP]     = ''
        attrs[ATTR_INTERVAL]           = ''
        attrs[ATTR_WAZE_TIME]          = ''
        attrs[ATTR_ZONE_DISTANCE]      = 1
        attrs[ATTR_CALC_DISTANCE]      = 1
        attrs[ATTR_WAZE_DISTANCE]      = 1
        attrs[ATTR_LAST_LOCATED]       = HHMMSS_ZERO
        attrs[ATTR_LAST_UPDATE_TIME]   = HHMMSS_ZERO
        attrs[ATTR_NEXT_UPDATE_TIME]   = HHMMSS_ZERO
        attrs[ATTR_POLL_COUNT]         = '0:0:0'
        attrs[ATTR_DIR_OF_TRAVEL]      = ''
        attrs[ATTR_TRAVEL_DISTANCE]    = 0
        attrs[ATTR_TRIGGER]            = ''
        attrs[ATTR_TIMESTAMP]          = dt_util.utcnow().isoformat()[0:19]
        attrs[ATTR_AUTHENTICATED]      = ''
        attrs[ATTR_BATTERY]            = 0
        attrs[ATTR_BATTERY_STATUS]     = ''
        attrs[ATTR_INFO]               = ''
        attrs[ATTR_ALTITUDE]           = 0
        attrs[ATTR_VERT_ACCURACY]  = 0
        attrs[ATTR_DEVICE_STATUS]      = ''
        attrs[ATTR_LOW_POWER_MODE]     = ''
        attrs[CONF_GROUP]              = self.group
        attrs[ATTR_PICTURE]            = self.badge_picture.get(devicename)
        attrs[ATTR_TRACKING]           = self.track_devicename_list
        attrs[ATTR_ICLOUD3_VERSION]    = VERSION

        return attrs

#--------------------------------------------------------------------
    def _initialize_zone_tables(self):
        '''
        Get friendly name of all zones to set the device_tracker state
        '''
        self.zones          = []
        self.zone_fname     = {"not_home": "Away", "near_zone": "NearZone"}
        self.zone_lat       = {}
        self.zone_long      = {}
        self.zone_radius_km = {}
        self.zone_radius_m  = {}
        self.zone_passive   = {}

        try:
            if self.start_icloud3_initial_load_flag == False:
                self.hass.services.call(ATTR_ZONE, "reload")
        except:
            pass

        log_msg = (f"Reloading Zone.yaml config file")
        self.log_debug_msg("*", log_msg)

        zones = self.hass.states.entity_ids(ATTR_ZONE)
        zone_msg = ''

        for zone in zones:
            zone_name  = zone.split(".")[1]      #zone='zone.'+zone_name

            try:
                self.zones.append(zone_name.lower())
                zone_data  = self.hass.states.get(zone).attributes
                self.log_debug_msg("*",f"zone-{zone_name}, data-{zone_data}")

                if instr(zone_name.lower(), STATIONARY):
                    self.zone_fname[zone_name] = 'Stationary'

                if ATTR_LATITUDE in zone_data:
                    self.zone_lat[zone_name]       = zone_data.get(ATTR_LATITUDE, 0)
                    self.zone_long[zone_name]      = zone_data.get(ATTR_LONGITUDE, 0)
                    self.zone_passive[zone_name]   = zone_data.get('passive', True)
                    self.zone_radius_m[zone_name]  = int(zone_data.get(ATTR_RADIUS, 100))
                    self.zone_radius_km[zone_name] = round(self.zone_radius_m[zone_name]/1000, 4)
                    self.zone_fname[zone_name]     = zone_data.get(ATTR_FRIENDLY_NAME, zone_name.title())

                else:
                    log_msg = (f"Error loading zone {zone_name} > No data was returned from HA. "
                               f"Zone data returned is `{zone_data}`")
                    self.log_error_msg(log_msg)
                    self._save_event("*", log_msg)

            except KeyError:
                self.zone_passive[zone_name] = False

            except Exception as err:
                _LOGGER.exception(err)

            zone_msg = (f"{zone_msg}{zone_name}/{self.zone_fname.get(zone_name)} "
                        f"(r{self.zone_radius_m[zone_name]} m), ")

        log_msg = (f"Set up Zones > {zone_msg[:-2]}")
        self._save_event_halog_info("*", log_msg)

        self.zone_home_lat    = self.zone_lat.get(HOME)
        self.zone_home_long   = self.zone_long.get(HOME)
        self.zone_home_radius_km = float(self.zone_radius_km.get(HOME))
        self.zone_home_radius_m  = self.zone_radius_m.get(HOME)

        self.base_zone        = HOME
        self.base_zone_name   = self.zone_fname.get(HOME)
        self.base_zone_lat    = self.zone_lat.get(HOME)
        self.base_zone_long   = self.zone_long.get(HOME)
        self.base_zone_radius_km = float(self.zone_radius_km.get(HOME))

        return

#--------------------------------------------------------------------
    def _define_stationary_zone_fields(self, stationary_inzone_interval_str,
                    stationary_still_time_str):
        #create dynamic zone used by ios app when stationary

        self.stat_zone_inzone_interval = self._time_str_to_secs(stationary_inzone_interval_str)
        self.stat_zone_still_time      = self._time_str_to_secs(stationary_still_time_str)
        self.stat_zone_half_still_time = self.stat_zone_still_time / 2
        self.in_stationary_zone_flag   = {}
        self.stat_zone_devicename_icon = {}  #icon to be used for a devicename
        self.stat_zone_moved_total     = {}  #Total of small distances
        self.stat_zone_timer           = {}  #Time when distance set to 0
        self.stat_min_dist_from_zone_km  = round(self.zone_home_radius_km * 2.5, 2)
        self.stat_dist_move_limit      = round(self.zone_home_radius_km * 1.5, 2)
        self.stat_zone_radius_km       = round(self.zone_home_radius_km * 2, 2)
        self.stat_zone_radius_m        = self.zone_home_radius_m * 2
        self.stat_zone_base_long       = self.zone_home_long

        #Offset the stat zone 1km north of Home if north of the equator or
        #1km south of Home is south of the equator. (offset of 0.005=1km degrees)
        #Switch direction if near the north or south pole.
        offset = STATIONARY_ZONE_HOME_OFFSET  #0.00468    #0.005=1km
        offset = -1*offset if self.zone_home_lat < 0 else offset
        offset = -1*offset if self.zone_home_lat > 89.8 or self.zone_home_lat < -89.8 else offset
        self.stat_zone_base_lat = self.zone_home_lat + offset

        log_msg = (f"Set Initial Stationary Zone Location > "
                   f"GPS-{format_gps(self.stat_zone_base_lat, self.stat_zone_base_long)}, "
                   f"Radius-{self.stat_zone_radius_m} m")
        self.log_debug_msg("*", log_msg)
        self._save_event("*", log_msg)

#--------------------------------------------------------------------
    def _initialize_debug_control(self, log_level):
        #string set using the update_icloud command to pass debug commands
        #into icloud3 to monitor operations or to set test variables
        #   interval - toggle display of interval calulation method in info fld
        #   debug - log 'debug' messages to the log file under the 'info' type
        #   debug_rawdata - log data read from records to the log file
        #   eventlog - Add debug items to ic3 event log
        #   debug+eventlog - Add debug items to HA log file and ic3 event log

        self.log_level_debug_flag         = (instr(log_level, 'debug') or DEBUG_TRACE_CONTROL_FLAG)
        self.log_level_debug_rawdata_flag = (instr(log_level, 'rawdata') and self.log_level_debug_flag)
        self.log_debug_msgs_trace_flag    = self.log_level_debug_flag

        self.log_level_intervalcalc_flag = DEBUG_TRACE_CONTROL_FLAG or instr(log_level, 'intervalcalc')
        self.log_level_eventlog_flag     = instr(log_level, 'eventlog')

        self.debug_counter = 0
        self.last_iosapp_msg = {} #can be used to compare changes in debug msgs

#########################################################
#
#   INITIALIZE PYICLOUD DEVICE API
#   DEVICE SETUP SUPPORT FUNCTIONS FOR MODES FMF, FAMSHR, IOSAPP
#
#########################################################
    def _initialize_pyicloud_device_api(self):
        #See if pyicloud_ic3 is available
        if (PYICLOUD_IC3_IMPORT_SUCCESSFUL == False and self.TRK_METHOD_FMF_FAMSHR):
            event_msg = ("iCloud3 Error > An error was encountered setting up the `pyicloud_ic3.py` "
                f"module. Either the module was not found or there was an error loading it."
                f"The {self.trk_method_short_name} Location Service is disabled and the "
                f"IOS App tracking_method will be used.")
            self._save_event_halog_error("*", event_msg)

            self._setup_iosapp_tracking_method()

        else:
            #Set up pyicloud cookies directory & file names
            try:
                self.icloud_cookies_dir  = self.hass.config.path(STORAGE_DIR, STORAGE_KEY_ICLOUD)
                self.icloud_cookies_file = (f"{self.icloud_cookies_dir}/"
                                            f"{self.username.replace('@','').replace('.','')}")
                if not os.path.exists(self.icloud_cookies_dir):
                    os.makedirs(self.icloud_cookies_dir)

            except Exception as err:
                _LOGGER.exception(err)

        if self.TRK_METHOD_IOSAPP:
            self.api = None

        elif self.TRK_METHOD_FMF_FAMSHR:
            event_msg = ("iCloud Web Services interface (pyicloud_ic3.py) > Verified")
            self._save_event_halog_info("*", event_msg)

            self._authenticate_pyicloud(initial_setup=True)

#--------------------------------------------------------------------
    def _authenticate_pyicloud(self, initial_setup=False):
        '''
        Authenticate the iCloud Acount via pyicloud
        If successful - self.api to the api of the pyicloudservice for the username
        If not        - set self.api = None
        '''
        try:
            self.count_pyicloud_authentications += 1
            self.authenticated_time = time.time()

            self.api = PyiCloudService(self.username, self.password,
                                       cookie_directory=self.icloud_cookies_dir,
                                       verify=True)
            self.time_pyicloud_calls += (time.time() - self.authenticated_time)

            event_msg = (f"{EVLOG_COLOR_AUTHENTICATE}iCloud Account Authentication Successful > {self.username}")
            self._save_event_halog_info("*", event_msg)

        except (PyiCloudFailedLoginException, PyiCloudNoDevicesException,
                PyiCloudAPIResponseException) as err:

            self.api = None
            self._setup_iosapp_tracking_method()

            event_msg = ("iCloud3 Error > An error was encountered authenticating the iCloud "
                f"account for {self.username}. The iCloud Web Services "
                f"may be down or the Username/Password may be invalid. "
                f"The {self.trk_method_short_name} Location Service "
                "is disabled and the IOS App tracking_method will be used.")
            self._save_event_halog_error("*", event_msg)

#--------------------------------------------------------------------
    def _setup_tracked_devices_for_fmf(self):
        '''
        Cycle thru the Find My Friends contact data. Extract the name, id &
        email address. Scan fmf_email config parameter to tie the fmf_id in
        the location record to the devicename.

                    email --> devicename <--fmf_id
        '''
        '''
        contact-{
            'emails': ['gary678tw@', 'gary_2fa_acct@email.com'],
            'firstName': 'Gary',
            'lastName': '',
            'photoUrl': 'PHOTO;X-ABCROP-RECTANGLE=ABClipRect_1&64&42&1228&1228&
                    //mOVw+4cc3VJSJmspjUWg==;
                    VALUE=uri:https://p58-contacts.icloud.com:443/186297810/wbs/
                    0123efg8a51b906789fece
            'contactId': '8590AE02-7D39-42C1-A2E8-ACCFB9A5E406',60110127e5cb19d1daea',
            'phones': ['(222)\xa0m456-7899'],
            'middleName': '',
            'id': 'ABC0DEFGH2NzE3'}

        cycle thru config>track_devices devicename/email parameter
        looking for a match with the fmf contact record emails item
                fmf_devicename_email:
                   'gary_iphone'       = 'gary_2fa_acct@email.com'
                   'gary_2fa_acct@email.com' = 'gary_iphone@'
             - or -
                   'gary_iphone'       = 'gary678@'
                   'gary678@'          = 'gary_iphone@gmail'

                emails:
                   ['gary456tw@', 'gary_2fa_acct@email.com]

        When complete, erase fmf_devicename_email and replace it with full
        email list
        '''
        try:
            device_obj = self.api.friends

            if device_obj == None:
                self._setup_iosapp_tracking_method()

                event_msg = (f"iCloud3 Error for {self.username} > "
                    "No FmF data was returned from Apple Web Services. "
                    "CRLF 1. Verify that the tracked devices have been added "
                    "to the Contacts list for this iCloud account."
                    "CRLF 2. Verify that the tracked devices have been set up in the "
                    "FindMe App and they can be located. "
                    "CRLF 3. See the iCloud3 Documentation, `Setting Up your iCloud "
                    "Account/Find-my-Friends Tracking Method`."
                    f"CRLFThe {self.trk_method_short_name} Location Service "
                    "is disabled and the IOS App tracking_method will be used.")
                self._save_event_halog_error("*", event_msg)

                return

            self.log_level_debug_rawdata("iCloud FmF Raw Data - (device_obj.data)", device_obj.data)

            #cycle thru al contacts in fmf recd
            devicename_contact_emails = {}
            contacts_valid_emails = ''

            #Get contacts data from non-2fa account. If there are no contacts
            #in the fmf data, use the following data in the fmf data
            for contact in device_obj.following:
                contact_emails = contact.get('invitationAcceptedHandles')
                contact_id     = contact.get('id')

                self.log_level_debug_rawdata("iCloud FmF Raw Data - (device_obj.following) 5715", contact)

                #cycle thru the emails on the tracked_devices config parameter
                for parm_email in self.fmf_devicename_email:
                    if instr(parm_email, '@') == False:
                        continue

                    #cycle thru the contacts emails
                    matched_friend = False
                    devicename = self.fmf_devicename_email.get(parm_email)

                    for contact_email in contact_emails:
                        #if contacts_valid_emails.find(contact_email) >= 0:
                        if instr(contacts_valid_emails, contact_email) == False:
                            contacts_valid_emails += contact_email + ", "

                        if contact_email.startswith(parm_email):
                            #update temp list with full email from contact recd
                            matched_friend = True
                            devicename_contact_emails[contact_email] = devicename
                            devicename_contact_emails[devicename]    = contact_email
                            #devicename_contact_emails[parm_email]   = devicename

                            self.fmf_id[contact_id] = devicename
                            self.fmf_id[devicename] = contact_id
                            self.devicename_verified[devicename] = True

                            log_msg = (f"Matched FmF Contact > "
                                       f"{self._format_fname_devicename(devicename)} "
                                       f"with {contact_email}, Id: {contact_id}")
                            self.log_info_msg(log_msg)
                            break

            for devicename in self.devicename_verified:
                if self.devicename_verified.get(devicename) is False:
                    parm_email = self.fmf_devicename_email.get(devicename)
                    devicename_contact_emails[devicename] = parm_email
                    log_msg = (f"iCloud3 Error for {self.username} > "
                        "Valid contact emails are {contacts_valid_emails[:-2]}")
                    self._save_event_halog_error("*", log_msg)
                    log_msg = (f"iCloud3 Error for {self.username} > "
                        f"The email address for {devicename} ({parm_email}) is invalid "
                        f"or is not in the FmF contact list.")
                    self._save_event_halog_error("*", log_msg)

            self.fmf_devicename_email = {}
            self.fmf_devicename_email.update(devicename_contact_emails)

        except Exception as err:
            self._setup_iosapp_tracking_method()
            _LOGGER.exception(err)

#--------------------------------------------------------------------
    def _setup_tracked_devices_for_famshr(self):
        '''
        Scan the iCloud devices data. Select devices based on the
        include & exclude devices and device_type config parameters.

        Extract the friendly_name & device_type from the icloud data
        '''
        try:
            api_devices = self.api.devices

            api_device_content = api_devices.response["content"]

        except (PyiCloudServiceNotActivatedException, PyiCloudNoDevicesException):
            self._setup_iosapp_tracking_method()

            event_msg = (f"iCloud3 Error for {self.username} > "
                f"No devices were returned from the iCloud Location Services. "
                f"iCloud {self.trk_method_short_name} Location Service is disabled. "
                f"iCloud3 will use the IOS App tracking_method instead.")
            self._save_event_halog_error("*", event_msg)
            return

        try:
            devicename_list_tracked = ''
            devicename_list_not_tracked = ''
            self.log_level_debug_rawdata("FamShr iCloud Data - (devices) 5784", api_device_content)

            for device in api_device_content:
                self.log_level_debug_rawdata("FamShr iCloud Data - (device) 5788", device)

                device_content_name = device[ATTR_NAME]
                devicename          = slugify(device_content_name)
                device_type         = device[ATTR_ICLOUD_DEVICE_CLASS]

                if devicename in self.devicename_verified:
                    self.devicename_verified[devicename] = True

                    self.api_device_devicename[device_content_name] = devicename
                    self.api_device_devicename[devicename]          = device_content_name

                    devicename_list_tracked = (f"{devicename_list_tracked} {device_content_name}/{devicename} ({device_type}), ")

                else:
                    devicename_list_not_tracked = (f"{devicename_list_not_tracked} {device_content_name} ({device_type}), ")

            if devicename_list_not_tracked != '':
                event_msg = (f"Not Tracking Devices > {devicename_list_not_tracked}")
                if devicename_list_tracked != '':
                    self._save_event_halog_info("*", event_msg)
                else:
                    event_msg = (f"iCloud3 Error > {event_msg}")
                    self._save_event_halog_error("*", event_msg)

            if devicename_list_tracked != '':
                event_msg = (f"Tracking Devices > {devicename_list_tracked}")
                self._save_event_halog_info("*", event_msg)

        except Exception as err:
            _LOGGER.exception(err)

            event_msg = (f"iCloud3 Error for {self.username} > "
                "Error Authenticating account or no data was returned from "
                "iCloud Web Services. Web Services may be down or the "
                "Username/Password may be invalid.")
            self._save_event_halog_error("*", event_msg)

#--------------------------------------------------------------------
    def _setup_tracked_devices_for_iosapp(self):
        '''
        The devices to be tracked are in the track_devices or the
        include_devices  config parameters.
        '''
        for devicename in self.devicename_verified:
            self.devicename_verified[devicename] = True

        return

 #--------------------------------------------------------------------
    def _setup_tracked_devices_config_parm(self, config_parameter):
        '''
        Set up the devices to be tracked and it's associated information
        for the configuration line entry. This will fill in the following
        fields based on the extracted devicename:
            device_type
            friendly_name
            fmf email address
            sensor.picture name
            device tracking flags
            tracked_devices list
        These fields may be overridden by the routines associated with the
        operating mode (fmf, icloud, iosapp)
        '''

        if config_parameter is None:
            return

        try:
            iosapp_v2_entities = self._get_entity_registry_entities('mobile_app')

        except Exception as err:
           # _LOGGER.exception(err)
           iosapp_v2_entities = []

        try:
            for track_device_line in config_parameter:
                di = self._decode_track_device_config_parms(
                            track_device_line, iosapp_v2_entities)

                if di is None:
                    return

                devicename = di[DI_DEVICENAME]
                if self._check_devicename_in_another_thread(devicename):
                    continue
                elif (self.iosapp_version.get(devicename) == 2 and
                        devicename == di[DI_DEVICENAME_IOSAPP]):
                    event_msg = (f"iCloud3 Error > iCloud3 not tracking {devicename}. "
                        f"The iCloud3 tracked_device is already assigned to "
                        f"the IOS App v2 and duplicate names are not allowed for HA "
                        f"Integration entities. You must change the IOS App v2 "
                        f"entity name on the HA `Sidebar>Configuration>Integrations` "
                        f"screen. Then do the following: "
                        f"CRLF 1. Select the Mobile_App entry for `{devicename}`."
                        f"CRLF 2. Scroll to the `device_tracker.{devicename}` statement."
                        f"CRLF 3. Select it."
                        f"CRLF 4. Click the Settings icon."
                        f"CRLF 5. Add or change the suffix of the "
                        f"`device_tracker.{devicename}` Entity ID to another value "
                        f"(e.g., _2, _10, _iosappv2)."
                        f"CRLF 6. Restart HA.")
                    self._save_event_halog_error("*", event_msg)
                    continue

                if di[DI_EMAIL]:
                    email = di[DI_EMAIL]
                    self.fmf_devicename_email[email]      = devicename
                    self.fmf_devicename_email[devicename] = email
                if di[DI_DEVICE_TYPE]:
                    self.device_type[devicename]          = di[DI_DEVICE_TYPE]
                if di[DI_NAME]:
                    self.fname[devicename]        = di[DI_NAME]
                if di[DI_BADGE_PICTURE]:
                    self.badge_picture[devicename]        = di[DI_BADGE_PICTURE]
                if di[DI_DEVICENAME_IOSAPP]:
                    self.devicename_iosapp[devicename]    = di[DI_DEVICENAME_IOSAPP]
                    self.devicename_iosapp_id[devicename] = di[DI_DEVICENAME_IOSAPP_ID]
                if di[DI_SENSOR_IOSAPP_TRIGGER]:
                    self.iosapp_v2_last_trigger_entity[devicename] = di[DI_SENSOR_IOSAPP_TRIGGER]
                if di[DI_ZONES]:
                    self.track_from_zone[devicename]      = di[DI_ZONES]
                if di[DI_SENSOR_PREFIX_NAME]:
                    self.sensor_prefix_name[devicename]   = di[DI_SENSOR_PREFIX_NAME]

                self.devicename_verified[devicename] = False

        except Exception as err:
            _LOGGER.exception(err)

#--------------------------------------------------------------------
    def _decode_track_device_config_parms(self,
                track_device_line, iosapp_v2_entities):
        '''
        This will decode the device's parameter in the configuration file for
        the include_devices, sensor_name_prefix, track_devices items in the
        format of:
           - devicename > email, picture, iosapp, sensornameprefix

        If the item cotains '@', it is an email item,
        If the item contains .png  or .jpg, it is a picture item.
        Otherwise, it is the prefix name item for sensors

        The device_type and friendly names are also returned in the
        following order as a list item:
            devicename, device_type, friendlyname, email, picture, sensor name

        Various formats:

        Find my Friends:
        ----------------
        devicename > email_address
        devicename > email_address, badge_picture_name
        devicename > email_address, badge_picture_name, iosapp_number, name
        devicename > email_address, iosapp_number
        devicename > email_address, iosapp_number, name
        devicename > email_address, badge_picture_name, name
        devicename > email_address, name

        Find my Phone:
        --------------
        devicename
        devicename > badge_picture_name
        devicename > badge_picture_name, name
        devicename > iosapp_number
        devicename > iosapp_number, name
        devicename > name


        IOS App Version 1:
        ------------------
        devicename
        devicename > badge_picture_name
        devicename > badge_picture_name, name

        IOS App Version 2:
        ------------------
        devicename
        devicename > iosapp_number
        devicename > badge_picture_name, iosapp_number
        devicename > badge_picture_name, iosapp_number, name
        '''

        try:
            email         = None
            badge_picture = None
            fname         = None
            scan_entity_registry = (iosapp_v2_entities is not [])
            iosappv2_id   = ''
            device_type   = None
            sensor_prefix = None
            zones         = []


            #devicename_parameters = track_device_line.lower().split('>')
            devicename_parameters = track_device_line.split('>')
            devicename  = slugify(devicename_parameters[0].replace(' ', '', 99).lower())
            log_msg = (f"Decoding > {track_device_line}")
            self._save_event_halog_info("*", log_msg)

            #If tracking method is IOSAPP or FAMSHR, try to make a friendly
            #name from the devicename. If FMF, it will be retrieved from the
            #contacts data. If it is specified on the config parms, it will be
            #overridden with the specified name later.

            fname, device_type = self._extract_name_device_type(devicename)
            self.tracked_devices_config_parm[devicename] = track_device_line

            if len(devicename_parameters) > 1:
                parameters = devicename_parameters[1].strip()
                parameters = parameters + ',,,,,,'
            else:
                parameters = ''

            items = parameters.split(',')
            for itemx in items:
                item_entered = itemx.strip().replace(' ', '_', 99)
                item = item_entered.lower()

                if item == '':
                    continue
                elif instr(item, '@'):
                    email = item
                elif instr(item, 'png') or instr(item, 'jpg'):
                    badge_picture = item
                elif item == 'iosappv1':
                    scan_entity_registry = False
                elif item.startswith("_"):
                    iosappv2_id = item
                elif isnumber(item):
                    iosappv2_id = "_" + item
                elif item in self.zones:
                    if item != HOME:
                        if zones == []:
                            zones = [item]
                        else:
                            zones.append(item)
                else:
                    fname = item_entered

            zones.append(HOME)
            if badge_picture and instr(badge_picture, '/') == False:
                badge_picture = '/local/' + badge_picture

            event_log = (f"Results > FriendlyName-{fname}, Email-{email}, "
                         f"Picture-{badge_picture}, DeviceType-{device_type}")
            if zones != []:
                event_log += f", TrackFromZone-{zones}"
            self._save_event("*", event_log)


            #Cycle through the mobile_app 'core.entity_registry' items and see
            #if this 'device_tracker.devicename' exists. If so, it is using
            #the iosapp v2 component. Return the devicename with the device suffix (_#)
            #and the sensor.xxxx_last_update_trigger entity for that device.
            device_id          = None
            v2er_devicename    = ''
            v2er_devicename_id = ''
            self.iosapp_version[devicename] = 1
            sensor_last_trigger_entity = ''

            #if using ios app v2, cycle through iosapp_v2_entities in
            #.storage/core.entity_registry (mobile_app pltform) and get the
            #names of the iosappv2 device_tracker and sensor.last_update_trigger
            #names for this devicename. If iosappv2_id is specified, look for
            #the device_tracker with that number.
            if scan_entity_registry:
                devicename_iosappv2_id = devicename + iosappv2_id
                log_msg = (f"Scanning {self.entity_registry_file} for entity registry for "
                    f"IOS App v2 device_tracker for {devicename_iosappv2_id}")
                if iosappv2_id != '':
                    log_msg += (f", devicename suffix specified ({iosappv2_id})")
                self.log_info_msg(log_msg)

                #Initial scan to find device_tracker.devicename record
                for entity in (x for x in iosapp_v2_entities \
                        if x['entity_id'].startswith("device_tracker.")):
                    v2er_devicename = entity['entity_id'].replace("device_tracker.", "", 5)
                    log_msg = (f"Checking {v2er_devicename} for {devicename_iosappv2_id}")
                    self.log_debug_msg(devicename, log_msg)
                    if iosappv2_id != '' and v2er_devicename != devicename_iosappv2_id:
                        continue

                    if (v2er_devicename.startswith(devicename) or
                            devicename.startswith(v2er_devicename)):
                        log_msg = (f"Matched IOS App v2 entity {v2er_devicename} with "
                                   f"iCloud3 tracked_device {devicename}")
                        self.log_info_msg(log_msg)

                        self.iosapp_version[devicename] = 2
                        device_id          = entity['device_id']
                        v2er_devicename_id = v2er_devicename.replace(devicename, '', 5)
                        break

                #Go back thru and look for sensor.last_update_trigger for deviceID
                if device_id:
                    for entity in (x for x in iosapp_v2_entities \
                            if instr(x['entity_id'], 'last_update_trigger')):

                        log_msg = (f"Checking {entity['entity_id']}")
                        #self.log_debug_msg(devicename, log_msg)

                        if (entity['device_id'] == device_id):
                            sensor_last_trigger_entity = entity['entity_id'].replace('sensor.', '', 5)
                            log_msg = (f"Matched IOS App v2  {entity['entity_id']} with "
                                       f"iCloud3 tracked_device {devicename}")
                            self.log_info_msg(log_msg)
                            break

            if self.iosapp_version[devicename] == 1:
                if scan_entity_registry:
                    event_msg = (f"Determine IOS App version > `device_tracker.{devicename_iosappv2_id}` "
                                 f"not found in Entity Registry IOS App v1 will be used.")
                    self._save_event("*", event_msg)
                v2er_devicename    = devicename
                v2er_devicename_id = ''
                sensor_last_trigger_entity = ''

            device_info = [devicename, device_type, fname, email, badge_picture,
                           v2er_devicename, v2er_devicename_id,
                           sensor_last_trigger_entity, zones, sensor_prefix]

            log_msg = (f"Extract Trk_Dev Parm, dev_info-{device_info}")
            self.log_debug_msg("*", log_msg)

        except Exception as err:
            _LOGGER.exception(err)

        return device_info
#--------------------------------------------------------------------
    def _get_entity_registry_entities(self, platform):
        '''
        Read the /config/.storage/core.entity_registry file and return
        the entities for platform ('mobile_app', 'ios', etc)
        '''

        try:
            if self.entity_registry_file == None:
                self.entity_registry_file  = self.hass.config.path(
                        STORAGE_DIR, STORAGE_KEY_ENTITY_REGISTRY)

            entities          = []
            entitity_reg_file = open(self.entity_registry_file)
            entitity_reg_str  = entitity_reg_file.read()
            entitity_reg_data = json.loads(entitity_reg_str)
            entitity_reg_entities = entitity_reg_data['data']['entities']
            entitity_reg_file.close()

            for entity in entitity_reg_entities:
                if (entity['platform'] == platform):
                    entities.append(entity)

        except Exception as err:
            _LOGGER.exception(err)
            pass

        return entities
#--------------------------------------------------------------------
    def _check_valid_ha_device_tracker(self, devicename):
        '''
        Validate the 'device_tracker.devicename' entity during the iCloud3
        Stage 2 initialization. If it does not exist, then it has not been set
        up in known_devices.yaml (and/or the iosapp) and can not be used ty
        the 'see' function thatupdates the location information.
        '''
        try:
            retry_cnt = 0
            entity_id = self._format_entity_id(devicename)

            while retry_cnt < 10:
                dev_data  = self.hass.states.get(entity_id)

                if dev_data:
                    dev_attrs = dev_data.attributes

                    if dev_attrs:
                        return True
                retry_cnt += 1

        #except (KeyError, AttributeError):
        #    pass

        except Exception as err:
            _LOGGER.exception(err)

        return False

#########################################################
#
#   DEVICE SENSOR SETUP ROUTINES
#
#########################################################
    def _setup_sensor_base_attrs(self, devicename, initial_load_flag):
        '''
        The sensor name prefix can be the devicename or a name specified on
        the track_device configuration parameter        '''

        if initial_load_flag == False:
            return

        self.sensor_prefix_name[devicename] = devicename

        attr_prefix_fname = self.sensor_prefix_name.get(devicename)

        #Format sensor['friendly_name'] attribute prefix
        attr_prefix_fname = attr_prefix_fname.replace('_','-').title()
        attr_prefix_fname = attr_prefix_fname.replace('Ip','-iP')
        attr_prefix_fname = attr_prefix_fname.replace('Iw','-iW')
        attr_prefix_fname = attr_prefix_fname.replace('--','-')

        self.sensor_attr_fname_prefix[devicename] = (f"{attr_prefix_fname}-")

        badge_attrs = {}
        badge_attrs['entity_picture'] = self.badge_picture.get(devicename)
        badge_attrs[ATTR_FRIENDLY_NAME]  = self.fname.get(devicename)
        badge_attrs['icon']           = SENSOR_ATTR_ICON.get('badge')
        self.sensor_badge_attrs[devicename] = badge_attrs

        for zone in self.track_from_zone.get(devicename):
            if zone == 'home':
                zone_prefix = ''
            else:
                zone_prefix = zone + '_'
            event_msg = (f"Sensor entity prefix > sensor.{zone_prefix} "
                         f"{self.sensor_prefix_name.get(devicename)}")
            self._save_event("*", event_msg)

        log_msg = (f"Set up sensor name for device, devicename-{devicename}, "
                    f"entity_base-{self.sensor_prefix_name.get(devicename)}")
        self.log_debug_msg(devicename, log_msg)

        return

#--------------------------------------------------------------------
    def _setup_sensors_custom_list(self, initial_load_flag):
        '''
        This will process the 'sensors' and 'exclude_sensors' config
        parameters if 'sensors' exists, only those sensors wil be displayed.
        if 'exclude_sensors' eists, those sensors will not be displayed.
        'sensors' takes ppresidence over 'exclude_sensors'.
        '''

        if initial_load_flag == False:
            return

        if self.sensor_ids != []:
            self.sensors_custom_list = []
            for sensor_id in self.sensor_ids:
                id = sensor_id.lower().strip()
                if id in SENSOR_ID_NAME_LIST:
                    self.sensors_custom_list.append(SENSOR_ID_NAME_LIST.get(id))

        elif self.exclude_sensor_ids != []:
            self.sensors_custom_list.extend(SENSOR_DEVICE_ATTRS)
            for sensor_id in self.exclude_sensor_ids:
                id = sensor_id.lower().strip()
                if id in SENSOR_ID_NAME_LIST:
                    if SENSOR_ID_NAME_LIST.get(id) in self.sensors_custom_list:
                        self.sensors_custom_list.remove(SENSOR_ID_NAME_LIST.get(id))
        else:
            self.sensors_custom_list.extend(SENSOR_DEVICE_ATTRS)


#########################################################
#
#   DEVICE STATUS SUPPORT FUNCTIONS FOR GPS ACCURACY, OLD LOC DATA, ETC
#
#########################################################
    def _check_old_loc_poor_gps(self, devicename, timestamp_secs, gps_accuracy):
        """
        If this is checked in the icloud location cycle,
        check if the location isold flag. Then check to see if
        the current timestamp is the same as the timestamp on the previous
        poll.

        If this is checked in the iosapp cycle,  the trigger transaction has
        already updated the lat/long so
        you don't want to discard the record just because it is old.
        If in a zone, use the trigger but check the distance from the
        zone when updating the device. If the distance from the zone = 0,
        then reset the lat/long to the center of the zone.
        """

        try:
            age     = int(self._secs_since(timestamp_secs))
            age_str = self._secs_to_time_str(age)
            location_isold_flag = (age > self.old_location_secs.get(devicename))
            poor_gps_flag       = (gps_accuracy > self.gps_accuracy_threshold)

            if (location_isold_flag == False and poor_gps_flag == False):
                self.old_loc_poor_gps_cnt[devicename]  = 0

            elif location_isold_flag or poor_gps_flag:
                self.old_loc_poor_gps_cnt[devicename] += 1

            self.poor_gps_accuracy_flag[devicename] = poor_gps_flag

            log_msg = (f"►CHECK ISOLD/GPS ACCURACY, Time-{self._secs_to_time(timestamp_secs)}, "
                        f"isOldFlag-{location_isold_flag}, Age-{age_str}, "
                        f"GPS Accuracy-{gps_accuracy}, GPSAccuracyFlag-{poor_gps_flag}")
            self.log_debug_msg(devicename, log_msg)

        except Exception as err:
            _LOGGER.exception(err)
            location_isold_flag = False
            self.poor_gps_accuracy_flag[devicename] = False
            self.old_loc_poor_gps_cnt[devicename]  = 0

            log_msg = ("►►INTERNAL ERROR (ChkOldLocPoorGPS)")
            self.log_error_msg(log_msg)

        return location_isold_flag

#--------------------------------------------------------------------
    def _check_poor_gps(self, devicename, gps_accuracy, location_isold_flag):
        '''
        If the GPS accuracy for the device's location is > the GPS
        threshold, set the device's GPS accuracy flag, increase the counter
        and prepare a record for the Event Log
        '''
        if gps_accuracy > self.gps_accuracy_threshold:
            self.poor_gps_accuracy_flag[devicename] = True
            self.old_loc_poor_gps_cnt[devicename] += 1

        else:
            self.poor_gps_accuracy_flag[devicename] = False

        if location_isold_flag == False:
            self.old_loc_poor_gps_cnt[devicename]  = 0

#--------------------------------------------------------------------
    def _check_next_update_time_reached(self, devicename = None):
        '''
        Cycle through the next_update_secs for all devices and
        determine if one of them is earlier than the current time.
        If so, the devices need to be updated.
        '''
        try:
            if self.next_update_secs is None:
                return None

            self.next_update_devicenames = []
            for devicename_zone in self.next_update_secs:
                if (devicename is None or devicename_zone.startswith(devicename)):
                    time_till_update = self.next_update_secs.get(devicename_zone) - \
                            self.this_update_secs
                    #self.next_update_in_secs[devicename_zone] = time_till_update

                    #debug_msg=f">>>CheckUpdtTime  {devicename}-{devicename_zone}-{time_till_update}-{self.next_update_devicenames}"
                    #self._save_event('*',debug_msg)
                    if time_till_update <= 5:
                        self.next_update_devicenames.append(devicename_zone.split(':')[0])

                        return (f"{devicename_zone.split(':')[0]}")
                        #return (f"{devicename_zone}@"
                        #        f"{self._secs_to_time(self.next_update_secs.get(devicename_zone))}")


        except Exception as err:
            _LOGGER.exception(err)

        return None

#--------------------------------------------------------------------
    def _check_in_zone_and_before_next_update(self, devicename):
        '''
        If updated because another device was updated and this device is
        in a zone and it's next time has not been reached, do not update now
        '''
        try:
            if (self.state_this_poll.get(devicename) != NOT_SET and
                    self._is_inzone(devicename) and
                    self._was_inzone(devicename) and
                    self._check_next_update_time_reached(devicename) is None):

                #log_msg = (f"{self._format_fname_devtype(devicename)} "
                #           f"Not updated, in zone {self.state_this_poll.get(devicename)}")
                #self.log_debug_msg(devicename, log_msg)
                #event_msg = (f"Not updated, already in Zone {self.state_this_poll.get(devicename)}")
                #self._save_event(devicename, event_msg)
                return True

        except Exception as err:
            _LOGGER.exception(err)

        return False

#--------------------------------------------------------------------
    def _check_outside_zone_no_exit(self,devicename, zone, latitude, longitude):
        '''
        If the device is outside of the zone and less than the zone radius + gps_acuracy_threshold
        and no Geographic Zone Exit trigger was received, it has probably wandered due to
        GPS errors. If so, discard the poll and try again later
        '''
        dist_from_zone_m  = self._zone_distance_m(
                                devicename,
                                zone,
                                latitude,
                                longitude)

        zone_radius_m = self.zone_radius_m.get(
                                zone,
                                self.zone_radius_m.get(HOME))
        zone_radius_accuracy_m = zone_radius_m + self.gps_accuracy_threshold

        if (dist_from_zone_m > zone_radius_m and
                dist_from_zone_m < zone_radius_accuracy_m and
                self.got_exit_trigger_flag.get(devicename) == False):
            self.poor_gps_accuracy_flag[devicename] = True

            discard_msg = ("Outside Zone and No Exit Zone trigger, "
                f"Keeping in zone > Zone-{zone}, "
                f"Distance-{dist_from_zone_m} m, "
                f"DiscardDist-{zone_radius_m} m to {zone_radius_accuracy_m} m ")

            return True, discard_msg

        return False, ''
#--------------------------------------------------------------------
    #@staticmethod
    def _get_interval_for_error_retry_cnt(self, retry_cnt):
        cycle, cycle_cnt = divmod(retry_cnt, 4)

        if cycle == 0:
            interval = 15
        elif cycle == 1:
            interval = 60           #1 min
        elif cycle == 2:
            interval = 300          #5 min
        elif cycle == 3:
            interval = 900          #15 min
        else:
            interval = 1800         #30 min

        return interval
#--------------------------------------------------------------------
    def _display_time_till_update_info_msg(self, devicename_zone, age_secs):
        info_msg = (f"●{self._secs_to_minsec_str(age_secs)}●")

        attrs = {}
        attrs[ATTR_NEXT_UPDATE_TIME] = info_msg

        self._update_device_sensors(devicename_zone, attrs)

#--------------------------------------------------------------------
    def _log_device_status_attrubutes(self, status):

        """
        Status-{'batteryLevel': 1.0, 'deviceDisplayName': 'iPhone X',
        'deviceStatus': '200', CONF_NAME: 'Gary-iPhone',
        'deviceModel': 'iphoneX-1-2-0', 'rawDeviceModel': 'iPhone10,6',
        'deviceClass': 'iPhone',
        'id':'qyXlfsz1BIOGxcqDxDleX63Mr63NqBxvJcajuZT3y05RyahM3/OMpuHYVN
        SUzmWV', 'lowPowerMode': False, 'batteryStatus': 'NotCharging',
        'fmlyShare': False, 'location': {'isOld': False,
        'isInaccurate': False, 'altitude': 0.0, 'positionType': 'GPS'
        'latitude': 27.726843548976, 'floorLevel': 0,
        'horizontalAccuracy': 48.00000000000001,
        'locationType': '', 'timeStamp': 1539662398966,
        'locationFinished': False, 'verticalAccuracy': 0.0,
        'longitude': -80.39036092533418}, 'locationCapable': True,
        'locationEnabled': True, 'isLocating': True, 'remoteLock': None,
        'activationLocked': True, 'lockedTimestamp': None,
        'lostModeCapable': True, 'lostModeEnabled': False,
        'locFoundEnabled': False, 'lostDevice': None,
        'lostTimestamp': '', 'remoteWipe': None,
        'wipeInProgress': False, 'wipedTimestamp': None, 'isMac': False}
        """

        log_msg = (f"►ICLOUD DATA, DEVICE ID-{status}, ▶deviceDisplayName-{status['deviceDisplayName']}")
        self.log_debug_msg('*', log_msg)

        location = status[ATTR_LOCATION]

        log_msg = (f"►ICLOUD DEVICE STATUS/LOCATION, "
            f"●deviceDisplayName-{status['deviceDisplayName']}, "
            f"●deviceStatus-{status[ATTR_ICLOUD_DEVICE_STATUS]}, "
            f"●name-{status[CONF_NAME]}, "
            f"●deviceClass-{status['deviceClass']}, "
            f"●batteryLevel-{status[ATTR_ICLOUD_BATTERY_LEVEL]}, "
            f"●batteryStatus-{status[ATTR_ICLOUD_BATTERY_STATUS]}, "
            f"●isOld-{location[ATTR_ISOLD]}, "
            f"●positionType-{location['positionType']}, "
            f"●latitude-{location[ATTR_LATITUDE]}, "
            f"●longitude-{location[ATTR_LONGITUDE]}, "
            f"●horizontalAccuracy-{location[ATTR_ICLOUD_HORIZONTAL_ACCURACY]}, "
            f"●timeStamp-{location[ATTR_ICLOUD_TIMESTAMP]}"
            f"({self._timestamp_to_time_utcsecs(location[ATTR_ICLOUD_TIMESTAMP])})")
        self.log_debug_msg('*', log_msg)
        return True

#--------------------------------------------------------------------
    def _log_start_finish_update_banner(self, start_finish_symbol, devicename,
                method, update_reason):
        '''
        Display a banner in the log file at the start and finish of a
        device update cycle
        '''

        log_msg = (f"^ {method} ^ {devicename}-{self.group}-{self.base_zone} ^^ "
                   f"State-{self.state_this_poll.get(devicename)} ^^ {update_reason} ^")

        log_msg2 = log_msg.replace('^', start_finish_symbol, 99).replace(" ",".").upper()
        self.log_debug_msg(devicename, log_msg2)

#########################################################
#
#   EVENT LOG ROUTINES
#
#########################################################
    def _setup_event_log_base_attrs(self, initial_load_flag):
        '''
        Set up the name, picture and devicename attributes in the Event Log
        sensor. Read the sensor attributes first to see if it was set up by
        another instance of iCloud3 for a different iCloud acount.
        '''
        #name_attrs = {}
        try:
            curr_base_attrs = self.hass.states.get(SENSOR_EVENT_LOG_ENTITY).attributes

            base_attrs = {k: v for k, v in curr_base_attrs.items()}

        except (KeyError, AttributeError):
            base_attrs         = {}
            base_attrs["logs"] = ""

        except Exception as err:
            _LOGGER.exception(err)

        try:
            name_attrs = {}
            if self.tracked_devices:
                for devicename in self.tracked_devices:
                    name_attrs[devicename] = self.fname.get(devicename)
            else:
                name_attrs = {'iCloud3 Startup Events': 'Error Messages'}

            if len(self.tracked_devices) > 0:
                self.log_table_max_items  = 999 * len(self.tracked_devices)

            base_attrs["names"] = name_attrs

            self.hass.states.set(SENSOR_EVENT_LOG_ENTITY, "Initialized", base_attrs)

            self.event_log_base_attrs = {k: v for k, v in base_attrs.items() if k != "logs"}
            self.event_log_base_attrs["logs"] = ""

        except Exception as err:
            _LOGGER.exception(err)

        return

#------------------------------------------------------
    def _save_event(self, devicename, event_text, column_left_hdr=None, column_right_hdr=None):
        '''
        Add records to the Event Log table the devicename. If the devicename="*",
        the event_text is added to all devicesnames table.

        The event_text can consist of pseudo codes that display a 2-column table (see
        _display_usage_counts function for an example and details)
        column_left_hdr & column_right_hdr display titles above the table columns in the
        state and interval areas if specified and indicate that a table is being created.

        The event_log lovelace card will display the event in a special color if
        the text starts with a special character:
        '''
        try:
            if (instr(event_text, "▼") or instr(event_text, "▲") or
                    instr(event_text, "event_log")):
                return

            devicename_zone  = self._format_devicename_zone(devicename, HOME)
            this_update_time = dt_util.now().strftime('%H:%M:%S')
            this_update_time = self._time_to_12hrtime(this_update_time, ampm=True)

            if devicename is None: devicename = '*'

            if column_left_hdr or column_right_hdr:
                state       = column_left_hdr
                zone        = ''
                interval    = column_right_hdr
                travel_time = ''
                distance    = ''

            elif self.start_icloud3_inprocess_flag:
                this_update_time = ''
                state       = ''
                zone_names  = ''
                zone        = ''
                interval    = ''
                travel_time = ''
                distance    = ''
                if instr(event_text, 'Stage') or instr(event_text, '^^^'):
                    pass
                else:
                    event_text  = f"• {event_text}"

            else:
                state       = self.state_this_poll.get(devicename) or ''
                zone_names  = self._get_zone_names(self.zone_current.get(devicename))
                zone        = zone_names[1] or ''
                interval    = self.interval_str.get(devicename_zone) or ''
                travel_time = self.last_tavel_time.get(devicename_zone) or ''
                distance    = self.last_distance_str.get(devicename_zone) or ''

            if instr(state, STATIONARY): state = STATIONARY
            if instr(zone, STATIONARY):  zone  = STATIONARY
            if len(event_text) == 0:     event_text = 'Info Message'

            if event_text.startswith('__'): event_text = event_text[2:]
            event_text = event_text.replace('"', '`')
            event_text = event_text.replace("'", "`")
            event_text = event_text.replace('~','--')
            event_text = event_text.replace('Background','Bkgnd')
            event_text = event_text.replace('Geographic','Geo')
            event_text = event_text.replace('Significant','Sig')

            #Keep track of special colors so it will continue on the
            #next text chunk
            color_symbol = ''
            if event_text.startswith('$'):   color_symbol = '$'
            if event_text.startswith('$$'):  color_symbol = '$'
            if event_text.startswith('$$$'): color_symbol = '$$$'
            if event_text.startswith('*'):   color_symbol = '*'
            if event_text.startswith('**'):  color_symbol = '**'
            if event_text.startswith('***'): color_symbol = '***'
            if instr(event_text, 'Error'):   color_symbol = '!'
            char_per_line = 250

            #Break the event_text string into chunks of 250 characters each and
            #create an event_log recd for each chunk
            if len(event_text) < char_per_line:
                event_recd = [devicename, this_update_time,
                                state, zone, interval, travel_time,
                                distance, event_text]
                self._insert_event_log_recd(event_recd)

            else:
                if event_text.find("CRLF") > 0:
                    split_str = "CRLF"
                else:
                    split_str = " "
                split_str_end_len = -1 * len(split_str)
                word_chunk = event_text.split(split_str)

                line_no=len(word_chunk)-1
                event_chunk = ''
                while line_no >= 0:
                    if len(event_chunk) + len(word_chunk[line_no]) + len(split_str) > char_per_line:
                        event_chunk = color_symbol + event_chunk
                        event_recd = [devicename, '', '', '', '', '', '',
                                        event_chunk[:split_str_end_len]]
                        self._insert_event_log_recd(event_recd)

                        event_chunk = ''

                    if len(word_chunk[line_no]) > 0:
                        event_chunk = word_chunk[line_no] + split_str + event_chunk

                    line_no-=1

                event_recd = [devicename, this_update_time,
                                state, zone, interval, travel_time,
                                distance, event_chunk[:split_str_end_len]]
                self._insert_event_log_recd(event_recd)



        except Exception as err:
            _LOGGER.exception(err)

#-------------------------------------------------------
    def _insert_event_log_recd(self, event_recd):
        """Add the event recd into the event table"""

        if self.event_log_table is None:
            self.event_log_table = []

        while len(self.event_log_table) >= self.log_table_max_items:
            self.event_log_table.pop()

        self.event_log_table.insert(0, event_recd)

#------------------------------------------------------
    def _update_event_log_sensor_line_items(self, devicename):
        """Display the event log"""

        try:
            if self.event_log_base_attrs:
                log_attrs = self.event_log_base_attrs.copy()

            attr_recd  = {}
            attr_event = {}
            log_attrs["log_level_debug"] = "On" if self.log_level_eventlog_flag else "Off"

            if devicename is None:
                return
            elif devicename == 'clear_log_items':
                log_attrs["filtername"] = "ClearLogItems"
            elif devicename == "*" :
                log_attrs["filtername"] = "Initialize"
            else:
                log_attrs["filtername"] = self.fname.get(devicename)
                #self.event_cnt[devicename] += 1

            #log_msg = (f"Updating Event Log for {devicename}")
            #self.log_debug_msg(devicename, log_msg)


            if devicename == 'clear_log_items':
                max_recds  = EVENT_LOG_CLEAR_CNT
                self.event_log_clear_secs = HIGH_INTEGER
                devicename = self.event_log_last_devicename
            else:
                max_recds = HIGH_INTEGER
                self.event_log_clear_secs = self.this_update_secs + EVENT_LOG_CLEAR_SECS
                self.event_log_last_devicename = devicename

            #The state must change for the recds to be refreshed on the
            #Lovelace card. If the state does not change, the new information
            #is not displayed. Add the update time to make it unique.

            log_update_time = (f"{dt_util.now().strftime('%a, %m/%d')}, "
                               f"{dt_util.now().strftime(self.um_time_strfmt)}")
            log_attrs["update_time"] = log_update_time
            self.event_log_sensor_state = (f"{devicename}:{log_update_time}")

            attr_recd = self._setup_event_log_event_recds(devicename, max_recds)
            log_attrs["logs"] = attr_recd

            self.hass.states.set(SENSOR_EVENT_LOG_ENTITY, self.event_log_sensor_state, log_attrs)

        except Exception as err:
            _LOGGER.exception(err)
#------------------------------------------------------
    def _setup_event_log_event_recds(self, devicename, max_recds=HIGH_INTEGER):
        '''
        Build the event items attribute for the event log sensor. Each item record
        is [devicename, time, state, zone, interval, travTime, dist, textMsg]
        Select the items for the devicename or '*' and return the string of
        the resulting list to be passed to the Event Log
        '''

        el_devicename_check=['*', devicename]

        attr_recd = [el_recd[1:8] for el_recd in self.event_log_table \
                if el_recd[0] in el_devicename_check]

        if max_recds == EVENT_LOG_CLEAR_CNT:
            recd_cnt = len(attr_recd)
            attr_recd = attr_recd[0:max_recds]
            control_recd = ['',' ',' ',' ',' ',' ',f'^^^ Click `Refresh` to display \
                                all records ({max_recds} of {recd_cnt} displayed) ^^^']
            attr_recd.insert(0, control_recd)

        control_recd = [HHMMSS_ZERO,'','','','','','Last Record']
        attr_recd.append(control_recd)

        return str(attr_recd)
#########################################################
#
#   WAZE ROUTINES
#
#########################################################
    def _get_waze_data(self, devicename,
                            this_lat, this_long, last_lat,
                            last_long, zone, last_dist_from_zone_km):

        try:
            if not self.distance_method_waze_flag:
                return ( WAZE_NOT_USED, 0, 0, 0)
            elif zone == self.base_zone:
                return (WAZE_USED, 0, 0, 0)
            elif self.waze_status == WAZE_PAUSED:
                return (WAZE_PAUSED, 0, 0, 0)

            try:
                waze_from_zone = self._get_waze_distance(devicename,
                        this_lat, this_long,
                        self.base_zone_lat, self.base_zone_long)

                waze_status = waze_from_zone[0]
                if waze_status == WAZE_NO_DATA:
                    event_msg = (f"Waze Route Failure > No Response from Waze Servers, "
                                 f"Calc distance will be used")
                    self._save_event(devicename, event_msg)

                    return (WAZE_NO_DATA, 0, 0, 0)

                waze_from_last_poll = self._get_waze_distance(devicename,
                        last_lat, last_long, this_lat, this_long)

            except Exception as err:
                _LOGGER.exception(err)

                if err == "Name 'WazeRouteCalculator' is not defined":
                    self.distance_method_waze_flag = False
                    return (WAZE_NOT_USED, 0, 0, 0)

                return (WAZE_NO_DATA, 0, 0, 0)

            try:
                waze_dist_from_zone_km = self._round_to_zero(waze_from_zone[1])
                waze_time_from_zone    = self._round_to_zero(waze_from_zone[2])
                waze_dist_last_poll    = self._round_to_zero(waze_from_last_poll[1])

                if waze_dist_from_zone_km == 0:
                    waze_time_from_zone = 0
                else:
                    waze_time_from_zone = self._round_to_zero(waze_from_zone[2])

                if ((waze_dist_from_zone_km > self.waze_max_distance) or
                     (waze_dist_from_zone_km < self.waze_min_distance)):
                    waze_status = WAZE_OUT_OF_RANGE

            except Exception as err:
                log_msg = (f"►►INTERNAL ERROR (ProcWazeData)-{err})")
                self.log_error_msg(log_msg)

            waze_time_msg = self._format_waze_time_msg(waze_time_from_zone)
            event_msg = (f"Waze Route Info: {self.zone_fname.get(self.base_zone)} > "
                         f"Dist-{waze_dist_from_zone_km} km, "
                         f"TravTime-{waze_time_msg}, "
                         f"DistMovedSinceLastUpdate-{waze_dist_last_poll} km")
            self._save_event(devicename, event_msg)

            log_msg = (f"►WAZE DISTANCES CALCULATED>, "
                      f"Status-{waze_status}, DistFromHome-{waze_dist_from_zone_km}, "
                      f"TimeFromHome-{waze_time_from_zone}, "
                      f"DistLastPoll-{waze_dist_last_poll}, "
                      f"WazeFromHome-{waze_from_zone}, WazeFromLastPoll-{waze_from_last_poll}")
            self.log_debug_interval_msg(devicename, log_msg)

            return (waze_status, waze_dist_from_zone_km, waze_time_from_zone,
                    waze_dist_last_poll)

        except Exception as err:
            log_msg = (f"►►INTERNAL ERROR (GetWazeData-{err})")
            self.log_info_msg(log_msg)

            return (WAZE_NO_DATA, 0, 0, 0)

#--------------------------------------------------------------------
    def _get_waze_distance(self, devicename, from_lat, from_long, to_lat,
                        to_long):
        """
        Example output:
            Time 72.42 minutes, distance 121.33 km.
            (72.41666666666667, 121.325)

        See https://github.com/home-assistant/home-assistant/blob
        /master/homeassistant/components/sensor/waze_travel_time.py
        See https://github.com/kovacsbalu/WazeRouteCalculator
        """

        try:
            from_loc = f"{from_lat},{from_long}"
            to_loc   = f"{to_lat},{to_long}"

            retry_cnt = 0
            while retry_cnt < 3:
                try:
                    self.count_waze_locates[devicename] += 1
                    waze_call_start_time = time.time()
                    route = WazeRouteCalculator.WazeRouteCalculator(
                            from_loc, to_loc, self.waze_region)

                    route_time, route_distance = \
                        route.calc_route_info(self.waze_realtime)

                    self.time_waze_calls[devicename] += (time.time() - waze_call_start_time)

                    route_time     = round(route_time, 0)
                    route_distance = round(route_distance, 2)

                    return (WAZE_USED, route_distance, route_time)

                except WazeRouteCalculator.WRCError as err:
                    retry_cnt += 1
                    log_msg = (f"Waze Server Error-{retry_cnt}, Retrying (#{err})")
                    self.log_info_msg(log_msg)

            return (WAZE_NO_DATA, 0, 0)

        except Exception as err:
            log_msg = (f"►►INTERNAL ERROR (GetWazeDist-{err})")
            self.log_info_msg(log_msg)

            return (WAZE_NO_DATA, 0, 0)
#--------------------------------------------------------------------
    def _get_waze_from_data_history(self, devicename,
                        curr_dist_from_zone_km, this_lat, this_long):
        '''
        Before getting Waze data, look at all other devices to see
        if there are any really close. If so, don't call waze but use their
        distance & time instead if the data it passes distance and age
        tests.

        The other device's distance from home and distance from last
        poll might not be the same as this devices current location
        but it should be close enough.

        last_waze_data is a list in the following format:
           [timestamp, latitudeWhenCalculated, longitudeWhenCalculated,
                [distance, time, distMoved]]

        Returns: [ Waze History Data]
        '''
        if not self.distance_method_waze_flag:
            return None
        elif self.waze_status == WAZE_PAUSED:
            return None

        #Calculate how far the old data can be from the new data before the
        #data will be refreshed.
        test_distance = curr_dist_from_zone_km * .05
        if test_distance > 5:
            test_distance = 5

        try:
            #other_closest_device_data = None
            used_data_from_devicename_zone = None
            for near_devicename_zone in self.waze_distance_history:
                devicename_zone = self._format_devicename_zone(devicename)
                self.waze_history_data_used_flag[devicename_zone] = False
                waze_data_other_device = self.waze_distance_history.get(near_devicename_zone)
                #Skip if this device doesn't have any Waze data saved or it's for
                #another base_zone.
                if len(waze_data_other_device) == 0:
                    continue
                elif len(waze_data_other_device[3]) == 0:
                    continue
                elif near_devicename_zone.endswith(':'+self.base_zone) == False:
                    continue

                waze_data_timestamp = waze_data_other_device[0]
                waze_data_latitude  = waze_data_other_device[1]
                waze_data_longitude = waze_data_other_device[2]

                dist_from_other_waze_data = self._calc_distance_km(
                            this_lat, this_long,
                            waze_data_latitude, waze_data_longitude)

                #Find device's waze data closest to my current location
                #If close enough, use it regardless of whose it is
                if dist_from_other_waze_data < test_distance:
                    used_data_from_devicename_zone = near_devicename_zone
                    other_closest_device_data      = waze_data_other_device[3]
                    test_distance                  = dist_from_other_waze_data

            #Return the waze history data for the other closest device
            if used_data_from_devicename_zone != None:
                used_devicename = used_data_from_devicename_zone.split(':')[0]
                event_msg = (f"Waze Route History Used: {self.zone_fname.get(self.base_zone)} > "
                             f"Dist-{other_closest_device_data[1]} km, "
                             f"TravTime-{round(other_closest_device_data[2], 0)} min, "
                             f"UsedInfoFrom-{self._format_fname_devicename(used_devicename)}, "
                             f"({test_distance} m AwayFromMyLoc)")
                self._save_event_halog_info(devicename, event_msg)

                #Return Waze data (Status, distance, time, dist_moved)
                self.waze_history_data_used_flag[used_data_from_devicename_zone] = True
                self.waze_data_copied_from[devicename_zone] = used_data_from_devicename_zone
                return other_closest_device_data

        except Exception as err:
            _LOGGER.exception(err)

        return None

#--------------------------------------------------------------------
    def _format_waze_time_msg(self, waze_time_from_zone):
        '''
        Return the message displayed in the waze time field ►►
        '''

        #Display time to the nearest minute if more than 3 min away
        if self.waze_status == WAZE_USED:
            t = waze_time_from_zone * 60
            r = 0
            if t > 180:
                t, r = divmod(t, 60)
                t = t + 1 if r > 30 else t
                t = t * 60

            waze_time_msg = self._secs_to_time_str(t)

        else:
            waze_time_msg = ''

        return waze_time_msg
#--------------------------------------------------------------------
    def _verify_waze_installation(self):
        '''
        Report on Waze Route alculator service availability
        '''

        self.log_info_msg("Verifying Waze Route Service component")

        if (WAZE_IMPORT_SUCCESSFUL == 'YES' and
                    self.distance_method_waze_flag):
            self.waze_status = WAZE_USED
        else:
            self.waze_status = WAZE_NOT_USED
            self.distance_method_waze_flag = False
            self.log_info_msg("Waze Route Service not available")
#########################################################
#
#   MULTIPLE PLATFORM/GROUP ROUTINES
#
#########################################################
    def _check_devicename_in_another_thread(self, devicename):
        '''
        Cycle through all instances of the ICLOUD3_TRACKED_DEVICES and check
        to see if  this devicename is also in another the tracked_devices
        for group/instance/thread/platform.
        If so, return True to reject this devicename and generate an error msg.

        ICLOUD3_TRACKED_DEVICES = {
            'work': ['gary_iphone > gcobb321@gmail.com, gary.png'],
            'group2': ['gary_iphone > gcobb321@gmail.com, gary.png, whse',
                       'lillian_iphone > lilliancobb321@gmail.com, lillian.png']}
        '''
        try:
            for group in ICLOUD3_GROUPS:
                if group != self.group and ICLOUD3_GROUPS.index(group) > 0:
                    tracked_devices = ICLOUD3_TRACKED_DEVICES.get(group)
                    for tracked_device in tracked_devices:
                        tracked_devicename = tracked_device.split('>')[0].strip()
                        if devicename == tracked_devicename:
                            log_msg = (f"Error: A device can only be tracked in "
                                f"one platform/group {ICLOUD3_GROUPS}. '{devicename}' was defined multiple "
                                f"groups and will not be tracked in '{self.group}'.")
                            self._save_event_halog_error('*', log_msg)
                            return True

        except Exception as err:
            _LOGGER.exception(err)

        return False

#######################################################################
#
#   EXTRACT ICLOUD3 PARAMETERS FROM THE CONFIG_IC3.YAML PARAMETER FILE.
#
#   The ic3 parameters are specified in the HA configuration.yaml file and
#   processed when HA starts. The 'config_ic3.yaml' file lets you specify
#   parameters at HA startup time or when iCloud3 is restarted using the
#   Restart-iC3 command on the Event Log screen. When iC3 is restarted,
#   the parameters will override those specified at HA startup time.
#
#   1. You can, for example, add new tracked devices without restarting HA.
#   2. You can specify the username, password and tracking method in this
#      file but these items are onlyu processed when iC3 initially loads.
#      A restart will discard these items
#
#######################################################################
    def _check_config_ic3_yaml_parameter_file(self):

        try:
            directory = os.path.abspath(os.path.dirname(__file__))
            config_ic3_filename=(f"{directory}/{self.config_ic3_file_name}")
            config_ic3_file = open(config_ic3_filename)

        except (FileNotFoundError, IOError):
            return

        except Exception as err:
            _LOGGER.exception(err)
            return

        try:
            parameter_list      = []
            parameter_list_name = ""
            log_success_msg     = ""
            log_error_msg       = ""
            success_msg         = ""
            error_msg           = ""
            for config_ic3_recd in config_ic3_file:
                parm_recd_flag = True
                recd = config_ic3_recd.strip()
                if len(recd) < 2 or recd.startswith('#'):
                    continue

                #Last recd started with a '-' (list item), Add this one to the list being built
                if recd.startswith('-'):
                    parameter_value = recd[1:].strip()
                    parameter_list.append(parameter_value)
                    continue

                #Not a list recd but a list exists, update it's parameter value, then process this recd
                elif parameter_list != []:
                    success_msg, error_msg = self._set_parameter_item(parameter_list_name, parameter_list)
                    log_success_msg += success_msg
                    log_error_msg   += error_msg
                    parameter_list_name = ""
                    parameter_list      = []

                #Decode and process the config recd
                recd_fields     = recd.split(":")
                parameter_name  = recd_fields[0].strip().lower()
                parameter_value = recd_fields[1].replace("'","").strip().lower()

                #Check to see if the parameter is a list parameter. If so start building a list
                if parameter_name in [CONF_TRACK_DEVICE, CONF_TRACK_DEVICES,
                                      CONF_CREATE_SENSORS, CONF_EXCLUDE_SENSORS]:
                    parameter_list_name = parameter_name
                else:
                    success_msg, error_msg = self._set_parameter_item(parameter_name, parameter_value)

                log_success_msg += success_msg
                log_error_msg   += error_msg

            if parameter_list != []:
                success_msg, error_msg = self._set_parameter_item(parameter_list_name, parameter_list)
                log_success_msg += success_msg
                log_error_msg   += error_msg

        except Exception as err:
            _LOGGER.exception(err)
            pass

        if log_error_msg != "":
            event_msg = (f"iCloud3 Error decoding `config_ic3.yaml` parameters > "
                         f"The following parameters can not be handled:CRLF{log_error_msg}")
            self._save_event_halog_info("*", event_msg)

        if log_success_msg != "" and self.start_icloud3_initial_load_flag == False:
            event_msg = (f"Processed `config_ic3.yaml` parameters >CRLF{log_success_msg}")
            self._save_event_halog_info("*", event_msg)

        return

#-------------------------------------------------------------------------
    def _set_parameter_item(self, parameter_name, parameter_value):
        try:
            success_msg = ""
            error_msg   = ""
             #These parameters can not be changed
            if parameter_name in [CONF_GROUP, CONF_USERNAME, CONF_PASSWORD,
                                  CONF_TRACKING_METHOD,
                                  CONF_CREATE_SENSORS, CONF_EXCLUDE_SENSORS,
                                  CONF_ENTITY_REGISTRY_FILE, CONF_CONFIG_IC3_FILE_NAME]:
                return ("", "")

            #if parameter_name == CONF_USERNAME:
            #    self.username = parameter_value
            #elif parameter_name == :
            #    self.password = parameter_value
            #    parameter_value = '********'
            #elif parameter_name == :
            #    self.tracking_method_config = parameter_value

            if parameter_name in [CONF_TRACK_DEVICES, CONF_TRACK_DEVICE]:
                self.track_devices = parameter_value
            elif parameter_name == CONF_MAX_IOSAPP_LOCATE_CNT:
                self.max_iosapp_locate_cnt = int(parameter_value)
            elif parameter_name == CONF_UNIT_OF_MEASUREMENT:
                self.unit_of_measurement = parameter_value
            elif parameter_name == CONF_BASE_ZONE:
                self.base_zone = parameter_value
            elif parameter_name == CONF_INZONE_INTERVAL:
                self.inzone_interval = self._time_str_to_secs(parameter_value)
            elif parameter_name == CONF_CENTER_IN_ZONE:
                self.center_in_zone_flag = (parameter_value == 'true')
            elif parameter_name == CONF_STATIONARY_STILL_TIME:
                self.stationary_still_time_str = parameter_value
            elif parameter_name == CONF_STATIONARY_INZONE_INTERVAL:
                self.stationary_inzone_interval_str = parameter_value
            elif parameter_name == CONF_TRAVEL_TIME_FACTOR:
                self.travel_time_factor = float(parameter_value)
            elif parameter_name == CONF_GPS_ACCURACY_THRESHOLD:
                self.gps_accuracy_threshold = int(parameter_value)
            elif parameter_name == CONF_OLD_LOCATION_THRESHOLD:
                self.old_location_threshold = self._time_str_to_secs(parameter_value)
            elif parameter_name == CONF_IGNORE_GPS_ACC_INZONE:
                self.ignore_gps_accuracy_inzone_flag = (parameter_value == 'true')
                self.check_gps_accuracy_inzone_flag = not self.ignore_gps_accuracy_inzone_flag
            elif parameter_name == CONF_WAZE_REGION:
                self.waze_region = parameter_value
            elif parameter_name == CONF_WAZE_MAX_DISTANCE:
                self.waze_max_distance = int(parameter_value)
            elif parameter_name == CONF_WAZE_MIN_DISTANCE:
                self.waze_min_distance = int(parameter_value)
            elif parameter_name == CONF_WAZE_REALTIME:
                self.waze_realtime = parameter_value
            elif parameter_name == CONF_DISTANCE_METHOD:
                self.distance_method_waze_flag = (parameter_value == 'waze')
            elif parameter_name == CONF_LOG_LEVEL:
                self._initialize_debug_control(parameter_value)
            else:
                error_msg = (f"{parameter_name}: {parameter_value}CRLF")

        except Exception as err:
            _LOGGER.exception(err)
            error_msg = (f"{err}CRLF")

        if error_msg == "":
            success_msg = (f"{parameter_name}: {parameter_value}CRLF")

        return (success_msg, error_msg)

#########################################################
#
#   log_, trace_ MESSAGE ROUTINES
#
#########################################################
    def log_info_msg(self, log_msg):
        if self.start_icloud3_inprocess_flag and not self.log_level_debug_flag:
            self.startup_log_msgs       += f"{self.startup_log_msgs_prefix}\n {log_msg}"
            self.startup_log_msgs_prefix = ""
        else:
            _LOGGER.info(log_msg)

        if (self.log_level_eventlog_flag and len(self.tracked_devices) > 0 and
                instr(log_msg, 'None (None)') == False):
            self._save_event(self.tracked_devices[0], (f"{EVLOG_COLOR_DEBUG}{str(log_msg).replace('►','')}"))

#--------------------------------------
    def _save_event_halog_info(self, devicename, log_msg):
        self._save_event(devicename, log_msg)

        if devicename != "*":
            log_msg = (f"{self._format_fname_devtype(devicename)} {log_msg}")

        if self.start_icloud3_inprocess_flag and not self.log_level_debug_flag:
            self.startup_log_msgs       += f"{self.startup_log_msgs_prefix}\n {log_msg}"
            self.startup_log_msgs_prefix = ""
        else:
            self.log_info_msg(log_msg)

#--------------------------------------
    def _save_event_halog_debug(self, devicename, log_msg):
        self._save_event(devicename, log_msg)

        if devicename != "*":
            log_msg = (f"{self._format_fname_devtype(devicename)} {log_msg}")
        self.log_debug_msg(devicename, log_msg)

#--------------------------------------
    @staticmethod
    def log_warning_msg(log_msg):
        _LOGGER.warning(log_msg)

#--------------------------------------
    @staticmethod
    def log_error_msg(log_msg):
        _LOGGER.error(log_msg)

#--------------------------------------
    def _save_event_halog_error(self, devicename, log_msg):
        if instr(log_msg, "iCloud3 Error"):
            self.info_notification = ICLOUD3_ERROR_MSG
            for devicename in self.tracked_devices:
                self._display_info_status_msg(devicename, ICLOUD3_ERROR_MSG)

        self._save_event(devicename, log_msg)
        log_msg = (f"{self._format_fname_devtype(devicename)} {log_msg}")

        if self.start_icloud3_inprocess_flag and not self.log_level_debug_flag:
            self.startup_log_msgs       += f"{self.startup_log_msgs_prefix}\n {log_msg}"
            self.startup_log_msgs_prefix = ""

        self.log_error_msg(log_msg)

#--------------------------------------
    def log_debug_msg(self, devicename, log_msg):
        if (self.log_level_eventlog_flag and instr(log_msg, 'None (None)') == False):
           self._save_event(devicename, (f"{EVLOG_COLOR_DEBUG}{str(log_msg).replace('►','')}"))

        if self.log_level_debug_flag:
            _LOGGER.info(f"◆{devicename}◆ {log_msg}")
        else:
            _LOGGER.debug(f"◆{devicename}◆ {log_msg}")

#--------------------------------------
    def log_debug_interval_msg(self, devicename, log_msg):
        if self.log_level_intervalcalc_flag:
            _LOGGER.debug(f"◆{devicename}◆ {log_msg}")

            if self.log_level_eventlog_flag:
                self._save_event(devicename, (f"{EVLOG_COLOR_DEBUG}{str(log_msg).replace('►','')}"))

#--------------------------------------
    def log_level_debug_rawdata(self, title, data):
        display_title = title.replace(" ",".").upper()
        if self.log_level_debug_rawdata_flag:
            log_msg = (f"▼---------▼--{display_title}--▼---------▼")
            self.log_debug_msg("*", log_msg)
            log_msg = (f"{data}")
            self.log_debug_msg("*", log_msg)
            log_msg = (f"▲---------▲--{display_title}--▲---------▲")
            self.log_debug_msg("*", log_msg)
#--------------------------------------
    def log_debug_msg2(self, log_msg):
            _LOGGER.debug(log_msg)

#--------------------------------------
    @staticmethod
    def _internal_error_msg(function_name, err_text: str='',
                section_name: str=''):
        log_msg = (f"►►INTERNAL ERROR-RETRYING ({function_name}:{section_name}-{err_text})")
        _LOGGER.error(log_msg)

        attrs = {}
        attrs[ATTR_INTERVAL]         = '0 sec'
        attrs[ATTR_NEXT_UPDATE_TIME] = HHMMSS_ZERO
        attrs[ATTR_INFO]             = log_msg

        return attrs

#########################################################
#
#   TIME & DISTANCE UTILITY ROUTINES
#
#########################################################
    @staticmethod
    def _time_now_secs():
        ''' Return the epoch seconds in utc time '''

        return int(time.time())
#--------------------------------------------------------------------
    def _secs_to_time(self, e_seconds, time_24h = False):
        """ Convert seconds to hh:mm:ss """

        if e_seconds == 0:
            return HHMMSS_ZERO
        else:
            t_struct = time.localtime(e_seconds + self.e_seconds_local_offset_secs)
            if time_24h:
                return  time.strftime("%H:%M:%S", t_struct).lstrip('0')
            else:
                return  time.strftime(self.um_time_strfmt, t_struct).lstrip('0')

#--------------------------------------------------------------------
    @staticmethod
    def _secs_to_time_str(secs):
        """ Create the time string from seconds """

        if secs < 60:
            time_str = str(round(secs, 0)) + " sec"
        elif secs < 3600:
            time_str = str(round(secs/60, 1)) + " min"
        elif secs == 3600:
            time_str = "1 hr"
        else:
            time_str = str(round(secs/3600, 1)) + " hrs"

        # xx.0 min/hr --> xx min/hr
        time_str = time_str.replace('.0 ', ' ')
        return time_str
#--------------------------------------------------------------------
    @staticmethod
    def _secs_to_minsec_str(secs):
        """ Create the time string from seconds """

        secs = int(secs)
        if secs < 60 and secs > 60:
            time_str = f"{secs}s"
        else:
            time_str = f"{int(secs/60)}m{(secs % 60)}s"

        return time_str
#--------------------------------------------------------------------
    def _secs_since(self, e_secs) -> int:
        #return self.this_update_secs - e_seconds

        return round(time.time() - e_secs)
#--------------------------------------------------------------------
    def _secs_to(self, e_secs) -> int:
        #return e_seconds - self.this_update_secs
        return round(e_secs - time.time())
#--------------------------------------------------------------------
    @staticmethod
    def _time_to_secs(hhmmss):
        """ Convert hh:mm:ss into seconds """
        if hhmmss:
            hh_mm_ss = hhmmss.split(":")
            secs = int(hh_mm_ss[0]) * 3600 + int(hh_mm_ss[1]) * 60 + int(hh_mm_ss[2])
        else:
            secs = 0

        return secs

#--------------------------------------------------------------------
    def _time_to_12hrtime(self, hhmmss, time_24h=False, ampm=False):
        #if hhmmss == HHMMSS_ZERO:
        #    return

        if self.unit_of_measurement == 'mi' and time_24h is False:
            hh_mm_ss = hhmmss.split(':')
            hhmmss_hh  = int(hh_mm_ss[0])

            ap = 'a'
            if hhmmss_hh > 12:
                hhmmss_hh -= 12
                ap = 'p'
            elif hhmmss_hh == 12:
                ap = 'p'
            elif hhmmss_hh == 0:
                hhmmss_hh = 12

            ap = '' if ampm == False else ap

            hhmmss = f"{hhmmss_hh}:{hh_mm_ss[1]}:{hh_mm_ss[2]}{ap}"
        return hhmmss
#--------------------------------------------------------------------
    @staticmethod
    def _time_str_to_secs(time_str='30 min') -> int:
        """
        Calculate the seconds in the time string.
        The time attribute is in the form of '15 sec' ',
        '2 min', '60 min', etc
        """

        s1 = str(time_str).replace('_', ' ') + " min"
        time_part = float((s1.split(" ")[0]))
        text_part = s1.split(" ")[1]

        if text_part == 'sec':
            secs = time_part
        elif text_part == 'min':
            secs = time_part * 60
        elif text_part == 'hrs':
            secs = time_part * 3600
        elif text_part in ('hr', 'hrs'):
            secs = time_part * 3600
        else:
            secs = 1200      #default to 20 minutes

        return secs

#--------------------------------------------------------------------
    def _timestamp_to_time_utcsecs(self, utc_timestamp) -> int:
        """
        Convert iCloud timeStamp into the local time zone and
        return hh:mm:ss
        """

        ts_local = int(float(utc_timestamp)/1000) + self.time_zone_offset_seconds
        hhmmss   = dt_util.utc_from_timestamp(ts_local).strftime(self.um_time_strfmt)
        if hhmmss[0] == "0":
            hhmmss = hhmmss[1:]

        return hhmmss

#--------------------------------------------------------------------
    def _timestamp_to_time(self, timestamp, time_24h = False):
        """
        Extract the time from the device timeStamp attribute
        updated by the IOS app.
        Format is --'timestamp': '2019-02-02 12:12:38.358-0500'
        Return as a 24hour time if time_24h = True
        """

        try:
            if timestamp == TIMESTAMP_ZERO:
                return HHMMSS_ZERO

            yyyymmdd_hhmmss = (f"{timestamp}.").split(' ')[1]
            hhmmss = yyyymmdd_hhmmss.split('.')[0]

            return hhmmss
        except:
            return HHMMSS_ZERO
#--------------------------------------------------------------------
    def _timestamp_to_secs_utc(self, utc_timestamp) -> int:
        """
        Convert timeStamp seconds (1567604461006) into the local time zone and
        return time in seconds.
        """

        ts_local = int(float(utc_timestamp)/1000) + self.time_zone_offset_seconds

        hhmmss = dt_util.utc_from_timestamp(ts_local).strftime('%X')
        if hhmmss[0] == "0":
            hhmmss = hhmmss[1:]

        return self._time_to_secs(hhmmss)

#--------------------------------------------------------------------
    @staticmethod
    def _secs_to_timestamp(secs):
        """
        Convert seconds to timestamp
        Return timestamp (2020-05-19 09:12:30)
        """
        time_struct = time.localtime(secs)

        return time.strftime("%Y-%m-%d %H:%M:%S", time_struct)

#--------------------------------------------------------------------
    def _timestamp_to_secs(self, timestamp, utc_local = LOCAL_TIME) -> int:
        """
        Convert the timestamp from the device timestamp attribute
        updated by the IOS app.
        Format is --'timestamp': '2019-02-02T12:12:38.358-0500'
        Return epoch seconds
        """
        try:
            if timestamp is None:
                return 0
            elif timestamp == '' or timestamp[0:19] == TIMESTAMP_ZERO:
                return 0

            timestamp = timestamp.replace("T", " ")[0:19]
            secs = time.mktime(time.strptime(timestamp, "%Y-%m-%d %H:%M:%S"))
            if utc_local is UTC_TIME:
                secs += self.time_zone_offset_seconds

        except Exception as err:
            _LOGGER.error(f"Invalid timestamp format, timestamp = '{timestamp}'")
            _LOGGER.exception(err)
            secs = 0

        return secs
#--------------------------------------------------------------------
    def _calculate_time_zone_offset(self):
        """
        Calculate time zone offset seconds
        """
        try:
            local_zone_offset = dt_util.now().strftime('%z')
            local_zone_offset_secs = int(local_zone_offset[1:3])*3600 + \
                        int(local_zone_offset[3:])*60
            if local_zone_offset[:1] == "-":
                local_zone_offset_secs = -1*local_zone_offset_secs

            t_now    = int(time.time())
            t_hhmmss = dt_util.now().strftime('%H%M%S')
            l_now    = time.localtime(t_now)
            l_hhmmss = time.strftime('%H%M%S', l_now)
            g_now    = time.gmtime(t_now)
            g_hhmmss = time.strftime('%H%M%S', g_now)

            if (l_hhmmss == g_hhmmss):
                self.e_seconds_local_offset_secs = local_zone_offset_secs

            log_msg = (f"Time Zone Offset, Local Zone-{local_zone_offset} hrs, "
                       f"{local_zone_offset_secs} secs")
            self.log_debug_msg('*', log_msg)

        except Exception as err:
            _LOGGER.exception(err)
            x = self._internal_error_msg(fct_name, err, 'CalcTZOffset')
            local_zone_offset_secs = 0

        return local_zone_offset_secs

#--------------------------------------------------------------------
    def _km_to_mi(self, arg_distance):
        arg_distance = arg_distance * self.um_km_mi_factor

        if arg_distance == 0:
            return 0
        elif arg_distance <= 20:
            return round(arg_distance, 2)
        elif arg_distance <= 100:
            return round(arg_distance, 1)
        else:
            return round(arg_distance)

    def _mi_to_km(self, arg_distance):
       return round(float(arg_distance) / self.um_km_mi_factor, 2)

#--------------------------------------------------------------------
    @staticmethod
    def _format_dist(dist):
        return f"{dist} km" if dist > .5 else f"{round(dist*1000)} m"

    @staticmethod
    def _format_dist_m(dist):
        return f"{round(dist/1000, 2)} km" if dist > 500 else f"{round(dist)} m"
#--------------------------------------------------------------------
    @staticmethod
    def _calc_distance_km(from_lat, from_long, to_lat, to_long):
        if from_lat == None or from_long == None or to_lat == None or to_long == None:
            return 0

        d = distance(from_lat, from_long, to_lat, to_long) / 1000
        if d < .05:
            d = 0
        return round(d, 2)

    @staticmethod
    def _calc_distance_m(from_lat, from_long, to_lat, to_long):
        if from_lat == None or from_long == None or to_lat == None or to_long == None:
            return 0

        d = distance(from_lat, from_long, to_lat, to_long)

        return round(d, 2)

#--------------------------------------------------------------------
    @staticmethod
    def _round_to_zero(arg_distance):
        if abs(arg_distance) < .05:
            arg_distance = 0
        return round(arg_distance, 2)

#--------------------------------------------------------------------
    def _add_comma_to_str(self, text):
        """ Add a comma to info if it is not an empty string """
        if text:
            return f"{text}, "
        return ''

#--------------------------------------------------------------------
    @staticmethod
    def _isnumber(string):

        try:
            test_number = float(string)

            return True
        except:
            return False

#--------------------------------------------------------------------
    @staticmethod
    def _inlist(string, list_items):

        for item in list_items:
            if string.find(item) >= 0:
                return True

        return False

    @staticmethod
    def _instr(string, find_string):
        return string.find(find_string) >= 0

#--------------------------------------------------------------------

    def _extract_name_device_type(self, devicename):
        '''Extract the name and device type from the devicename'''

        try:
            fname    = devicename.title()
            device_type = ''

            for dev_type in APPLE_DEVICE_TYPES:
                if instr(devicename, dev_type):
                    fnamew = devicename.replace(dev_type, "", 99)
                    fname  = fnamew.replace("_", "", 99)
                    fname  = fname.replace("-", "", 99).title()
                    device_type  = dev_type
                    return (fname, dev_type)

        except Exception as err:
            _LOGGER.exception(err)

        return (fname, "iCloud")

#########################################################
#
#   These functions handle notification and entry of the
#   iCloud Account trusted device verification code.
#
#########################################################
    def icloud_show_trusted_device_request_form(self):
        """We need a trusted device."""
        configurator = self.hass.components.configurator

        log_msg = (f"Get Trusted Device, User={self.username}, Config={self.hass_configurator_request_id}")
        self.log_debug_msg('*', log_msg)

        #Exit if verification in process
        if self.username in self.hass_configurator_request_id:
            return

        device_list = ''
        self.trusted_device_list = {"Error": None}
        if self.trusted_device_list.get("Error") != None:
            device_list = '\n\n'\
                '----------------------------------------------\n'\
                '●●● Previous Trusted Device Id Entry is Invalid ●●●\n\n\n' \
                '----------------------------------------------\n\n\n'
            #self.valid_trusted_device_ids = None
            self.trusted_device_list = {"Error": None}

        self.trusted_devices = self.api.trusted_devices
        device_list += "ID&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Phone Number\n" \
                      "––&nbsp;&nbsp;&nbsp;&nbsp;––––––––––––\n"

        log_msg = (f"Trusted Device={self.trusted_devices}")
        self.log_debug_msg('*', log_msg)

        for device in self.trusted_devices:
            device_list += (f"{device['deviceId']}&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"
                            f"&nbsp;&nbsp;{device.get('phoneNumber')}\n")

            #self.valid_trusted_device_ids = (f"{i},{self.valid_trusted_device_ids}")
            self.trusted_device_list[device['deviceId']] = device

        log_msg = (f"Valid Trusted IDs={self.trusted_device_list}")
        self.log_debug_msg('*', log_msg)

        description_msg = (f"Account {self.username} needs to be verified. Enter the "
                           f"ID for the Trusted Device that will receive the "
                           f"verification code via a text message.\n\n\n{device_list}")

        self.hass_configurator_request_id[self.username] = configurator.request_config(
            (f"Select iCloud Trusted Device"),
            self.icloud_handle_trusted_device_entry,
            description    = (description_msg),
            entity_picture = "/static/images/config_icloud.png",
            submit_caption = 'Confirm',
            fields         = [{'id': 'trusted_device', \
                               CONF_NAME: 'Trusted Device ID'}]
        )

#--------------------------------------------------------------------
    def icloud_handle_trusted_device_entry(self, callback_data):
        """
        Take the device number enterd above, get the api.device info and
        have pyiCloud validate the device.

        callbackData-{'trusted_device': '1'}
        apiDevices=[{'deviceType': 'SMS', 'areaCode': '', 'phoneNumber':
                    '********65', 'deviceId': '1'},
                    {'deviceType': 'SMS', 'areaCode': '', 'phoneNumber':
                    '********66', 'deviceId': '2'}]
        """
        device_id_entered = callback_data.get('trusted_device')
        if device_id_entered not in self.trusted_device_list:
            event_msg = (f"iCloud3 Error > Invalid Trusted Device ID, "
                         f"Entered-{device_id_entered}")
            self._save_event_halog_error("*", event_msg)

            self.trusted_device = None
            self.trusted_device_list["Error"] = str(device_id_entered)
            return
            #self.icloud_show_trusted_device_request_form()

        self.trusted_device = self.trusted_device_list[device_id_entered]

        if self.username not in self.hass_configurator_request_id:
            request_id   = self.hass_configurator_request_id.pop(self.username)
            configurator = self.hass.components.configurator
            configurator.request_done(request_id)

        elif not self.api.send_verification_code(self.trusted_device):
            event_msg = ("iCloud3 Error > Failed to send verification code")
            self._save_event_halog_error("*", event_msg)

            self.trusted_device = None
            self.valid_trusted_device_ids = None

        else:
            # Get the verification code, Trigger the next step immediately
            self.icloud_show_verification_code_entry_form()

#------------------------------------------------------
    def icloud_show_verification_code_entry_form(self):
        """Return the verification code."""
        configurator = self.hass.components.configurator
        if self.username in self.hass_configurator_request_id:
            request_id   = self.hass_configurator_request_id.pop(self.username)
            configurator = self.hass.components.configurator
            configurator.request_done(request_id)
            #return

        self.hass_configurator_request_id[self.username] = configurator.request_config(
            (f"Enter iCloud Verification Code"),
            self.icloud_handle_verification_code_entry,
            description    = ('Enter the Verification Code sent to the Trusted Device'),
            entity_picture = "/static/images/config_icloud.png",
            submit_caption = 'Confirm',
            fields         = [{'id': 'code', \
                               CONF_NAME: 'Verification Code'}]
        )

#--------------------------------------------------------------------
    def icloud_handle_verification_code_entry(self, callback_data):
        """Handle the chosen trusted device."""
        from .pyicloud_ic3 import PyiCloudException
        self.verification_code = callback_data.get('code')

        try:
            if not self.api.validate_verification_code(
                    self.trusted_device, self.verification_code):
                raise PyiCloudException('Unknown failure')
        except PyiCloudException as error:
            # Reset to the initial 2FA state to allow the user to retry
            log_msg = (f"iCloud3 Error > Failed to verify verification "
                       f"code: {error}")
            self.log_error_msg(log_msg)

            self.trusted_device = None
            self.verification_code = None

            # Trigger the next step immediately
            self.icloud_show_trusted_device_request_form()

        if self.username in self.hass_configurator_request_id:
            request_id   = self.hass_configurator_request_id.pop(self.username)
            configurator = self.hass.components.configurator
            configurator.request_done(request_id)

#--------------------------------------------------------------------
    def icloud_authenticate_account(self, restarting_flag = False):
        '''
        Make sure iCloud is still available and doesn't need to be reauthenticated
        in 15-second polling loop

        Returns True  if Authentication is needed.
        Returns False if Authentication succeeded
        '''

        if self.TRK_METHOD_IOSAPP:
            return False
        elif self.start_icloud3_inprocess_flag:
            return False

        fct_name = "icloud_authenticate_account"

        from .pyicloud_ic3 import PyiCloudService

        try:
            if restarting_flag is False:
                if self.api is None:
                    event_msg = ("iCloud/FmF API Error, No device API information "
                                    "for devices. Resetting iCloud")
                    self._save_event_halog_error(event_msg)

                    self._start_icloud3()

                elif self.start_icloud3_request_flag:    #via service call
                    event_msg = ("iCloud Restarting, Reset command issued")
                    self._save_event_halog_error(event_msg)
                    self._start_icloud3()

                if self.api is None:
                    event_msg = ("iCloud reset failed, no device API information "
                                    "after reset")
                    self._save_event_halog_error(event_msg)

                    return True

            if self.api.requires_2sa:
                from .pyicloud_ic3 import PyiCloudException
                try:
                    if self.trusted_device is None:
                        self.icloud_show_trusted_device_request_form()
                        return True  #Authentication needed

                    if self.verification_code is None:
                        self.icloud_show_verification_code_entry_form()

                        devicename = list(self.tracked_devices.keys())[0]
                        self._display_info_status_msg(devicename, '')
                        return True  #Authentication needed

                    self.api.authenticate()
                    self.authenticated_time = time.time()

                    event_msg = (f"iCloud/FmF Authentication, Devices-{self.api.devices}")
                    self._save_event_halog_info("*", event_msg)

                    if self.api.requires_2sa:
                        raise Exception('Unknown failure')

                    self.trusted_device    = None
                    self.verification_code = None

                except PyiCloudException as error:
                    event_msg = (f"iCloud3 Error > Setting up 2FA: {error}")
                    self._save_event_halog_error(event_msg)

                    return True  #Authentication needed, Authentication Failed

            return False         #Authentication not needed, (Authenticationed OK)

        except Exception as err:
            _LOGGER.exception(err)
            x = self._internal_error_msg(fct_name, err, 'AuthiCloud')
            return True

#########################################################
#
#   ICLOUD ROUTINES
#
#########################################################
    def service_handler_lost_iphone(self, group, arg_devicename):
        """Call the lost iPhone function if the device is found."""

        if self.TRK_METHOD_FAMSHR is False:
            log_msg = ("Lost Phone Alert Error: Alerts can only be sent "
                       "when using tracking_method FamShr")
            self.log_warning_msg(log_msg)
            self.info_notification = log_msg
            self._display_status_info_msg(arg_devicename, log_msg)
            return

        valid_devicename = self._service_multi_acct_devicename_check(
                "Lost iPhone Service", group, arg_devicename)
        if valid_devicename is False:
            return

        device = self.tracked_devices.get(arg_devicename)
        device.play_sound()

        log_msg = (f"iCloud Lost iPhone Alert, Device {arg_devicename}")
        self.log_info_msg(log_msg)
        self._display_status_info_msg(arg_devicename, "Lost Phone Alert sent")

#--------------------------------------------------------------------
    def service_handler_icloud_update(self, group, arg_devicename=None,
                    arg_command=None):
        """
        Authenticate against iCloud and scan for devices.


        Commands:
        - waze reset range = reset the min-max rnge to defaults (1-1000)
        - waze toggle      = toggle waze on or off
        - pause            = stop polling for the devicename or all devices
        - resume           = resume polling devicename or all devices, reset
                             the interval override to normal interval
                             calculations
        - pause-resume     = same as above but toggles between pause and resume
        - zone xxxx        = updates the devie state to xxxx and updates all
                             of the iloud3 attributes. This does the see
                             service call and then an update.
        - reset            = reset everything and rescans all of the devices
        - debug interval   = displays the interval formula being used
        - debug gps        = simulates bad gps accuracy
        - debug old        = simulates that the location informaiton is old
        - info xxx         = the same as 'debug'
        - location         = request location update from ios app
        """

        #If several iCloud groups are used, this will be called for each
        #one. Exit if this instance of iCloud is not the one handling this
        #device. But if devicename = 'reset', it is an event_log service cmd.
        log_msg = (f"iCloud3 Command Entered, Device: {arg_devicename}, "
                 f"Command: {arg_command}")
        self.log_debug_msg("*", log_msg)

        if arg_devicename:
            if (arg_devicename != 'restart'):
                valid_devicename = self._service_multi_acct_devicename_check(
                    "Update iCloud Service", group, arg_devicename)
                if valid_devicename is False:
                    return

        if instr(arg_command, 'event_log') == False:
            self._save_event(arg_devicename,
                        f"Service Call Command Received > {arg_command}")

        arg_command         = (f"{arg_command} .")
        arg_command_cmd     = arg_command.split(' ')[0].lower()
        arg_command_parm    = arg_command.split(' ')[1]       #original value
        arg_command_parmlow = arg_command_parm.lower()
        log_level_msg       = ""

        log_msg = (f"iCloud3 Command Processed > Device-{arg_devicename} ({group}), "
                   f"Command-{arg_command}")

        #System level commands
        if arg_command_cmd == 'restart':
            if self.tracked_devices == []:
                self._start_icloud3()
            elif self.start_icloud3_inprocess_flag is False:
                self.start_icloud3_request_flag = True
            self._save_event_halog_info("*", log_msg)
            return

        elif arg_command_cmd == 'refresh_event_log':
            self._update_event_log_sensor_line_items(arg_devicename)
            return

        elif arg_command_cmd == 'event_log':
            error_msg = ("Error > Then refresh the Event Log page in your browser. v2.1 "
                         "has [Refresh] [Debug] [Restart-ic3] at the top. "
                         "Also, swipe down in the iOS App to refresh it on your devices.")
            self._save_event("*", error_msg)
            error_msg = ("Error > Event Log v1.0 is being used. Clear your browser "
                         "cache or add `?v=2.1` to the ui-lovelace.yaml so it reads "
                         "`- url: .../icloud3-event-log-card.js?v=2.1`. ")
            self._save_event("*", error_msg)

            self._update_event_log_sensor_line_items(arg_devicename)
            return

        elif arg_command_cmd == "counts":
            for devicename in self.count_update_iosapp:
                self._display_usage_counts(devicename)
            return

        elif arg_command_cmd == 'trusted_device':
            self.icloud_show_trusted_device_request_form()
            return

        #command preprocessor, reformat specific commands
        elif instr(arg_command_cmd, 'log_level'):
            if instr(arg_command_parm, 'debug'):
                self.log_level_debug_flag = (not self.log_level_debug_flag)

            if instr(arg_command_parm, 'rawdata'):
                self.log_level_debug_rawdata_flag = (not self.log_level_debug_rawdata_flag)
                if self.log_level_debug_rawdata_flag: self.log_level_debug_flag = True

            log_level_debug = "On" if self.log_level_debug_flag else "Off"
            log_msg += f"(Debug Log-{log_level_debug})"
            self._save_event_halog_info("*", log_msg)

            if instr(arg_command_parm, 'intervalcalc'):
                self.log_level_intervalcalc_flag = (not self.log_level_intervalcalc_flag)

            if instr(arg_command_parm, 'eventlog'):
                self.log_level_eventlog_flag = (not self.log_level_eventlog_flag)

                #log_level_debug = "On" if self.log_level_eventlog_flag else "Off"
                #log_msg += f"(iC3 Event Log/Debug Items-{log_level_debug})"
                #self._save_event_halog_info("*", log_msg)

            return

        self._save_event_halog_info("*", log_msg)

        #Location level commands
        if arg_command_cmd == 'waze':
            if self.waze_status == WAZE_NOT_USED:
                arg_command_cmd = ''
                return
            elif arg_command_parmlow == 'reset_range':
                self.waze_min_distance = 0
                self.waze_max_distance = HIGH_INTEGER
                self.waze_manual_pause_flag = False
                self.waze_status = WAZE_USED
            elif arg_command_parmlow == 'toggle':
                if self.waze_status == WAZE_PAUSED:
                    self.waze_manual_pause_flag = False
                    self.waze_status = WAZE_USED
                else:
                    self.waze_manual_pause_flag = True
                    self.waze_status = WAZE_PAUSED
            elif arg_command_parmlow == 'pause':
                self.waze_manual_pause_flag = False
                self.waze_status = WAZE_USED
            elif arg_command_parmlow != 'pause':
                self.waze_manual_pause_flag = True
                self.waze_status = WAZE_PAUSED

        elif arg_command_cmd == 'zone':     #parmeter is the new zone
            #if HOME in arg_command_parmlow:    #home/not_home is lower case
            if self.base_zone in arg_command_parmlow:    #home/not_home is lower case
                arg_command_parm = arg_command_parmlow

            kwargs = {}
            attrs  = {}

            self._wait_if_update_in_process(arg_devicename)
            self.overrideinterval_seconds[arg_devicename] = 0
            self.update_in_process_flag = False
            self._initialize_next_update_time(arg_devicename)

            self._update_device_icloud('Command', arg_devicename)

            return

        #Device level commands
        device_time_adj = 0
        for devicename in self.tracked_devices:
            if arg_devicename and devicename != arg_devicename:
                continue

            device_time_adj += 3
            devicename_zone = self._format_devicename_zone(devicename, HOME)

            now_secs_str = dt_util.now().strftime('%X')
            now_seconds  = self._time_to_secs(now_secs_str)
            x, update_in_secs = divmod(now_seconds, 15)
            update_in_secs = 15 - update_in_secs + device_time_adj

            attrs = {}

            #command processor, execute the entered command
            info_msg = None
            if arg_command_cmd == 'pause':
                cmd_type = CMD_PAUSE
                self.next_update_secs[devicename_zone] = HIGH_INTEGER
                self.next_update_time[devicename_zone] = PAUSED
                self._display_info_status_msg(devicename, '● PAUSED ●')

            elif arg_command_cmd == 'resume':
                cmd_type = CMD_RESUME
                self.next_update_time[devicename_zone]    = HHMMSS_ZERO
                self.next_update_secs[devicename_zone]    = 0
                #self._initialize_next_update_time(devicename)
                self.overrideinterval_seconds[devicename] = 0
                self._display_info_status_msg(devicename, '● RESUMING ●')
                self._update_device_icloud('Resuming', devicename)

            elif arg_command_cmd == 'waze':
                cmd_type = CMD_WAZE
                if self.waze_status == WAZE_USED:
                    self.next_update_time[devicename_zone] = HHMMSS_ZERO
                    self.next_update_secs[devicename_zone] = 0
                    #self._initialize_next_update_time(devicename)
                    attrs[ATTR_NEXT_UPDATE_TIME]           = HHMMSS_ZERO
                    attrs[ATTR_WAZE_DISTANCE]              = 'Resuming'
                    self.overrideinterval_seconds[devicename] = 0
                    self._update_device_sensors(devicename, attrs)
                    attrs = {}

                    self._update_device_icloud('Resuming', devicename)
                else:
                    attrs[ATTR_WAZE_DISTANCE] = PAUSED
                    attrs[ATTR_WAZE_TIME]     = ''

            elif arg_command_cmd == ATTR_LOCATION:
                self._request_iosapp_location_update(devicename)

            else:
                cmd_type = CMD_ERROR
                info_msg = (f"● INVALID COMMAND > {arg_command_cmd} ●")
                self._display_info_status_msg(devicename, info_msg)

            if attrs:
                self._update_device_sensors(devicename, attrs)

        #end for devicename in devs loop

#--------------------------------------------------------------------
    def service_handler_icloud_setinterval(self, group, arg_interval=None,
                    arg_devicename=None):

        """
        Set the interval or process the action command of the given devices.
            'interval' has the following options:
                - 15               = 15 minutes
                - 15 min           = 15 minutes
                - 15 sec           = 15 seconds
                - 5 hrs            = 5 hours
                - Pause            = Pause polling for all devices
                                     (or specific device if devicename
                                      is specified)
                - Resume            = Resume polling for all devices
                                     (or specific device if devicename
                                      is specified)
                - Waze              = Toggle Waze on/off
        """
        #If several iCloud groups are used, this will be called for each
        #one. Exit if this instance of iCloud is not the one handling this
        #device.

        if arg_devicename and self.TRK_METHOD_IOSAPP:
            if self.count_request_iosapp_locate.get(arg_devicename) > self.max_iosapp_locate_cnt:
                event_msg = (f"Can not Set Interval, location request cnt "
                             f"exceeded ({self.count_request_iosapp_locate.get(arg_devicename)} "
                             f"of { self.max_iosapp_locate_cnt})")
                self._save_event(arg_devicename, event_msg)
                return

        elif arg_devicename:
            valid_devicename = self._service_multi_acct_devicename_check(
                "Update Interval Service", group, arg_devicename)
            if valid_devicename is False:
                return

        if arg_interval is None:
            if arg_devicename is not None:
                self._save_event(arg_devicename, "Set Interval Command Error, "
                        "no new interval specified")
            return

        cmd_type = CMD_INTERVAL
        new_interval = arg_interval.lower().replace('_', ' ')

#       loop through all devices being tracked and
#       update the attributes. Set various flags if pausing or resuming
#       that will be processed by the next poll in '_polling_loop_15_sec_icloud'
        device_time_adj = 0
        for devicename in self.tracked_devices:
            if arg_devicename and devicename != arg_devicename:
                continue

            device_time_adj += 3
            devicename_zone = self._format_devicename_zone(devicename, HOME)

            self._wait_if_update_in_process()

            log_msg = (f"►SET INTERVAL COMMAND Start {devicename}, "
                f"ArgDevname-{arg_devicename}, ArgInterval-{arg_interval}, "
                f"New Interval-{new_interval}")
            self.log_debug_msg(devicename, log_msg)
            self._save_event(devicename,
                    (f"Set Interval Command handled, New interval {arg_interval}"))

            self.next_update_time[devicename_zone] = HHMMSS_ZERO
            self.next_update_secs[devicename_zone] = 0
            #self._initialize_next_update_time(devicename)
            self.interval_str[devicename_zone]        = new_interval
            self.overrideinterval_seconds[devicename] = self._time_str_to_secs(new_interval)

            now_seconds = self._time_to_secs(dt_util.now().strftime('%X'))
            x, update_in_secs = divmod(now_seconds, 15)
            time_suffix = 15 - update_in_secs + device_time_adj

            info_msg = '● Updating ●'
            self._display_info_status_msg(devicename, info_msg)

            log_msg = (f"►SET INTERVAL COMMAND END {devicename}")
            self.log_debug_msg(devicename, log_msg)
#--------------------------------------------------------------------
    def _service_multi_acct_devicename_check(self, svc_call_name,
            group, arg_devicename):

        if arg_devicename is None:
            log_msg = (f"{svc_call_name} Error, no devicename specified")
            self.log_error_msg(log_msg)
            return False

        info_msg = (f"Checking {svc_call_name} for {group}")

        if (arg_devicename not in self.track_devicename_list):
            event_msg = (f"{info_msg}, {arg_devicename} not in this group")
            #self._save_event(arg_devicename, event_msg)
            self.log_info_msg(event_msg)
            return False

        event_msg = (f"{info_msg}-{arg_devicename} Processed")
        #self._save_event(arg_devicename, event_msg)
        self.log_info_msg(event_msg)
        return True
#--------------------------------------------------------------------