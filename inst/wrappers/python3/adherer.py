#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Mar 12 21:59:57 2018

The adherer module interfaces with the R package AdhereR
using a standard shell-and-files approach.

@author: Dan Dediu, ddediu@gmail.com
"""

# Imports
import warnings
import subprocess
import os
import numbers
import datetime
import tempfile
import atexit
import platform
import shutil
import pandas
from PIL import Image

# Windows=specific registry access:
if platform.system() == "Windows":
    import winreg


# pylint: disable=too-many-instance-attributes
# pylint: disable=too-many-arguments
# pylint: disable=R0914
# pylint: disable=too-many-statements
# pylint: disable=too-many-return-statements
# pylint: disable=too-many-branches
# pylint: disable=C0302
# pylint: disable=C0103
# pylint: disable=R1705
# pylint: disable=W0703
# pylint: disable=W0603
# We need these here (even if they might not be seen as too elegant).


# The AdhereR R package name, minimum required version, and external call function:
_R_PACKAGE_NAME = 'AdhereR' # package name
_R_PACKAGE_MIN_VERSION = '0.1.1' # minimum version
_R_PACKAGE_EXTERNAL_CALL_FUNCTION = 'callAdhereR' # function interfacing with non-R callers


class CallAdhereRError(Exception):
    """Error occuring when calling AhereR"""
    pass


# Check if Rscript is ok and works (returns True if so, otherwise False)
def _check_rscript(path):
    if path is None:
        # must not be None:
        return False
    if not (os.path.isfile(path) and os.access(path, os.X_OK)):
        # must exist and be executable:
        return False
    # try to execute it:
    try:
        subprocess.call(path)
    except subprocess.CalledProcessError:
        return False
    return True

# Check if for the given Rscript, the right AdhereR package is installed:
def _check_r_package_ahderer_is_installed(path_to_rscript):
    if not _check_rscript(path_to_rscript):
        return False
    # Is AdhereR installed and has the right version?
    # Call adhereR:
    rscript_cmd = '"' + path_to_rscript + '"' + ' --vanilla -e ' + \
                  '"if(!require(' + _R_PACKAGE_NAME + '))' + \
                  ' {quit(save=\'no\',status=10)}; ' + \
                  'if( compareVersion(\'' + _R_PACKAGE_MIN_VERSION + '\', '+ \
                  'as.character(packageVersion(\'' + _R_PACKAGE_NAME + '\'))) > 0 ) ' + \
                  '{quit(save=\'no\',status=11)}; ' + \
                  'quit(save=\'no\',status=0);"'
    return_code = subprocess.call(rscript_cmd, shell=True)

    if return_code == 10:
        warnings.warn('adhereR: the AdhereR package is not installed for ' + \
                      'the version of R given by "' + path_to_rscript + '". ' + \
                      'Please install at least version ' + _R_PACKAGE_MIN_VERSION + \
                      ' or manually give another Rscript location through the ' + \
                      '"set_rscript_path()" function!')
        return False
    elif return_code == 11:
        warnings.warn('adhereR: the AdhereR package installed for ' + \
                      'the version of R given by "' + path_to_rscript + '" ' + \
                      'must be at least version ' + _R_PACKAGE_MIN_VERSION + '. ' + \
                      'Please install at least version ' + _R_PACKAGE_MIN_VERSION + \
                      ' or manually give another Rscript location through the ' + \
                      '"set_rscript_path()" function!')
        return False
    else:
        return True

# On Windows, check if a given registry key points to a viable Rscript
def _check_rscript_win_registry(reg_class, reg_key, is64bits):
    _r_reg_path = None
    try:
        _r_regkey = winreg.OpenKey(reg_class,
                                   reg_key,
                                   0,
                                   winreg.KEY_READ + (winreg.KEY_WOW64_64KEY if is64bits else 0))
        _r_reg_curver = winreg.QueryValueEx(_r_regkey, r"Current Version")
        _r_regkey = winreg.OpenKey(reg_class,
                                   reg_key + '\\' + str(_r_reg_curver[0]),
                                   0,
                                   winreg.KEY_READ + (winreg.KEY_WOW64_64KEY if is64bits else 0))
        _r_reg_path = winreg.QueryValueEx(_r_regkey, r"InstallPath")
    except Exception:
        return None
    if not _r_reg_path is None:
        _r_reg_path = str(_r_reg_path[0]) + "bin\\" + ("x64\\" if is64bits else "") + "Rscript.exe"
        return _r_reg_path if _check_rscript(_r_reg_path) else None
    else:
        return None

# Try to automatically detect R/Rscript
# from https://support.rstudio.com/hc/en-us/articles/200486138-Using-Different-Versions-of-R
def _autodetect_rscript():
    _os_name = platform.system()
    if _os_name == "Darwin": # macOS
        # first, attempt 'which'
        _path = shutil.which('Rscript')
        if _check_rscript(_path):
            return _path
        else:
            # otherwise, fallback to the standard locations:
            _path = None
            for _path in ['/usr/bin/Rscript',
                          '/usr/local/bin/Rscript',
                          '/opt/local/bin/Rscript',
                          '/Library/Frameworks/R.framework/Versions/Current/Resources/bin/Rscript']:
                if _check_rscript(_path):
                    return _path # found!
            # not found:
            return None
    elif _os_name == "Linux": # linux
        # first, attempt 'which'
        _path = shutil.which('Rscript')
        if _check_rscript(_path):
            return _path
        else:
            # otherwise, fallback to the standard locations:
            _path = None
            for _path in ['/usr/bin/Rscript',
                          '/usr/local/bin/Rscript',
                          '/opt/local/bin/Rscript',
                          '~/bin/Rscript']:
                if _check_rscript(_path):
                    return _path # found!
            # not found:
            return None
    elif _os_name == "Windows": # windows
        # first, attempt 'which'
        _path = shutil.which('Rscript')
        if _check_rscript(_path):
            return _path
        else:
            # otherwise, look in the registry:
            # the relevant infor should be in
            # HKEY_LOCAL_MACHINE\Software\R-core\R or
            # HKEY_CURRENT_USER\Software\R-core\R
            # and the relevant values are:
            # "Current Version" and "[Current Version]\InstallPath"
            # however, the are several complications, namely:
            # 1. HKEY_CURRENT_USER and HKEY_LOCAL_MACHINE
            # 2. 32 vs 64 bits R (i.e., there might be R, R32 and R64 registry entries)
            # 3. accessing the registry from Python depends on 32 vs 64 bits Python and Windows!

            # are we on a 64 bits Windows?
            is64bits = (platform.machine().upper() == "AMD64")

            # check various registry keys sequentially (use a list of lists with class and key):
            _reg_keys = [[winreg.HKEY_CURRENT_USER, r"SOFTWARE\R-core\R"],
                         [winreg.HKEY_CURRENT_USER, r"SOFTWARE\R-core\R32"],
                         [winreg.HKEY_CURRENT_USER, r"SOFTWARE\R-core\R64"],
                         [winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\R-core\R"],
                         [winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\R-core\R32"],
                         [winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\R-core\R64"]]
            _path = None
            for reg_key in _reg_keys:
                _path = _check_rscript_win_registry(reg_key[0], reg_key[1], is64bits)
                if not _path is None:
                    return _path # found!
            # not found:
            return None
    else:
        # Unknown OS:
        warnings.warn('Unknown Operating System "' + _os_name + '": ' +\
                      'this currenty runs only on Windows, macOS and Linux.')
        return None

# Try to autodetect RScript on this sytem:
_RSCRIPT_PATH = _autodetect_rscript()
if _RSCRIPT_PATH is None:
    warnings.warn('The automatic detection of "Rscript" on your system failed: '
                  'please make sure you do have a functioning "R" installed and '
                  'manually locate "Rscript" (should be in the same location as "R"). '
                  'Make sure you pass the full path (including "Rscript") to the '
                  '"adherer" package through the "set_rscript_path()" function!')
# And check if AdhereR is installed there as well:
if not _check_r_package_ahderer_is_installed(_RSCRIPT_PATH):
    _RSCRIPT_PATH = None # reset the path to None

# Getters and setters for _RSCRIPT_PATH:
def set_rscript_path(path):
    """
    Manually set the path to Rscript.
    Used if autodetection fails or if need to explicitely use a non-default R installation.
    """
    global _RSCRIPT_PATH
    _RSCRIPT_PATH = path

def get_rscript_path():
    """
    Get the path to Rscript.
    """
    global _RSCRIPT_PATH
    return _RSCRIPT_PATH


# Try to use the temporary folder as data directory:
_DATA_SHARING_DIRECTORY = None
try:
    _DATA_SHARING_DIRECTORY = tempfile.TemporaryDirectory(prefix='adherer-')
except Exception:
    warnings.warn('The automatic creation of the temporary directory for data exchange '
                  'between python and R failed. Please give a directory with read and write '
                  'access by passing the full path to the ' + \
                  '"set_data_sharing_directory()" function!')
    _DATA_SHARING_DIRECTORY = None

# Getters and setters for _DATA_SHARING_DIRECTORY:
def set_data_sharing_directory(path):
    """
    Manually set the directory for data exchange.
    This directory MUST exist and have read & wrote access for the current user.
    """
    global _DATA_SHARING_DIRECTORY
    _DATA_SHARING_DIRECTORY = path

def get_data_sharing_directory():
    """
    Get the directory for data exchange.
    """
    global _DATA_SHARING_DIRECTORY
    if isinstance(_DATA_SHARING_DIRECTORY, tempfile.TemporaryDirectory):
        return _DATA_SHARING_DIRECTORY.name
    else:
        return _DATA_SHARING_DIRECTORY

@atexit.register
def _adherer_cleanup():
    # Cleanup at the end of the module:
    if not (_DATA_SHARING_DIRECTORY is None) and \
       isinstance(_DATA_SHARING_DIRECTORY, tempfile.TemporaryDirectory):
        _DATA_SHARING_DIRECTORY.cleanup()


class CMA0(object):
    """
    The CMA base class
    """

    # What CMA class ("function") is this?:
    _adherer_function = 'CMA0'

    def __init__(self,
                 dataset,
                 id_colname,
                 event_date_colname,
                 event_duration_colname,
                 event_daily_dose_colname=None,
                 medication_class_colname=None,
                 carryover_within_obs_window=False,
                 carryover_into_obs_window=False,
                 carry_only_for_same_medication=False,
                 consider_dosage_change=False,
                 medication_change_means_new_treatment_episode=False,
                 maximum_permissible_gap=180,
                 maximum_permissible_gap_unit='days',
                 followup_window_start_type='numeric',
                 followup_window_start=0,
                 followup_window_start_unit='days',
                 followup_window_duration_type='numeric',
                 followup_window_duration=365*2,
                 followup_window_duration_unit='days',
                 observation_window_start_type='numeric',
                 observation_window_start=0,
                 observation_window_start_unit='days',
                 observation_window_duration_type='numeric',
                 observation_window_duration=365*2,
                 observation_window_duration_unit='days',
                 sliding_window_start_type='numeric',
                 sliding_window_start=0,
                 sliding_window_start_unit='days',
                 sliding_window_duration_type='numeric',
                 sliding_window_duration=90,
                 sliding_window_duration_unit='days',
                 sliding_window_step_duration_type='numeric',
                 sliding_window_step_duration=30,
                 sliding_window_step_unit='days',
                 sliding_window_no_steps=None,
                 cma_to_apply=None,
                 date_format='%m/%d/%Y',
                 event_interval_colname='event.interval',
                 gap_days_colname='gap.days',
                 force_na_cma_for_failed_patients=True,
                 keep_window_start_end_dates=False,
                 remove_events_outside_followup_window=True,
                 keep_event_interval_for_all_events=False,
                 parallel_backend='none',
                 parallel_threads='auto',
                 suppress_warnings=False,
                 save_event_info=False,
                 na_symbol_numeric='NA',
                 na_symbol_string='NA',
                 logical_symbol_true='TRUE',
                 logical_symbol_false='FALSE',
                 colnames_dot_symbol='.',
                 colnames_start_dot='.',
                 path_to_rscript=get_rscript_path(),
                 path_to_data_directory=get_data_sharing_directory(),
                 print_adherer_messages=True):

        # Store the parameter values:
        self._dataset = dataset
        self._id_colname = id_colname
        self._event_date_colname = event_date_colname
        self._event_duration_colname = event_duration_colname
        self._event_daily_dose_colname = event_daily_dose_colname
        self._medication_class_colname = medication_class_colname
        self._carryover_within_obs_window = carryover_within_obs_window
        self._carryover_into_obs_window = carryover_into_obs_window
        self._carry_only_for_same_medication = carry_only_for_same_medication
        self._consider_dosage_change = consider_dosage_change
        self._medication_change_means_new_treatment_episode = \
            medication_change_means_new_treatment_episode
        self._maximum_permissible_gap = maximum_permissible_gap
        self._maximum_permissible_gap_unit = maximum_permissible_gap_unit
        self._followup_window_start_type = followup_window_start_type
        self._followup_window_start = followup_window_start
        self._followup_window_start_unit = followup_window_start_unit
        self._followup_window_duration_type = followup_window_duration_type
        self._followup_window_duration = followup_window_duration
        self._followup_window_duration_unit = followup_window_duration_unit
        self._observation_window_start_type = observation_window_start_type
        self._observation_window_start = observation_window_start
        self._observation_window_start_unit = observation_window_start_unit
        self._observation_window_duration_type = observation_window_duration_type
        self._observation_window_duration = observation_window_duration
        self._observation_window_duration_unit = observation_window_duration_unit
        self._sliding_window_start_type = sliding_window_start_type
        self._sliding_window_start = sliding_window_start
        self._sliding_window_start_unit = sliding_window_start_unit
        self._sliding_window_duration_type = sliding_window_duration_type
        self._sliding_window_duration = sliding_window_duration
        self._sliding_window_duration_unit = sliding_window_duration_unit
        self._sliding_window_step_duration_type = sliding_window_step_duration_type
        self._sliding_window_step_duration = sliding_window_step_duration
        self._sliding_window_step_unit = sliding_window_step_unit
        self._sliding_window_no_steps = sliding_window_no_steps
        self._cma_to_apply = cma_to_apply
        self._date_format = date_format
        self._event_interval_colname = event_interval_colname
        self._gap_days_colname = gap_days_colname
        self._force_na_cma_for_failed_patients = force_na_cma_for_failed_patients
        self._keep_window_start_end_dates = keep_window_start_end_dates
        self._remove_events_outside_followup_window = remove_events_outside_followup_window
        self._keep_event_interval_for_all_events = keep_event_interval_for_all_events
        self._parallel_backend = parallel_backend
        self._parallel_threads = parallel_threads
        self._suppress_warnings = suppress_warnings
        self._save_event_info = save_event_info
        self._na_symbol_numeric = na_symbol_numeric
        self._na_symbol_string = na_symbol_string
        self._logical_symbol_true = logical_symbol_true
        self._logical_symbol_false = logical_symbol_false
        self._colnames_dot_symbol = colnames_dot_symbol
        self._colnames_start_dot = colnames_start_dot
        self._path_to_rscript = path_to_rscript
        self._path_to_data_directory = path_to_data_directory
        self._print_adherer_messages = print_adherer_messages

        # CMA-specific stuff:
        self._cma = None
        self._event_info = None
        self._treatment_episodes = None
        self._plot_image = None
        self._computation_return_code = None
        self._computation_messages = None

    # Printing:
    def __repr__(self):
        return "CMA object of type " + self._adherer_function + \
               " (on " + str(self._dataset.shape[0]) + " rows)."

    # Accessors:
    def get_dataset(self):
        """
        Get the original dataset used for computations.

        Returns
        -------
        A pandas table with the dataset, or None.

        """
        return self._dataset

    def get_cma(self):
        """
        Get the computed CMA.

        Returns
        -------
        A pandas table with the CMA if computed, or None.

        """
        return self._cma

    def get_event_info(self):
        """
        Get the event info.

        Returns
        -------
        A pandas table with the event info if computed, or None.

        """
        return self._event_info

    def get_treatment_episodes(self):
        """
        Get the treatment episodes.

        Returns
        -------
        A pandas table with the treatment episodes if computed, or None.

        """
        return self._treatment_episodes

    def get_computation_results(self):
        """
        Get the results of calling AdhereR.

        Returns
        -------
        A dictionary with entries 'code' (the numeric code returned by the
        shell process) and 'messages' (a string contining the actual messages
        produced by AdhereR).

        """
        return {'code':self._computation_return_code, 'messages':self._computation_messages}

    def compute_event_int_gaps(self):
        """
        Compute the event intervals and gaps (intended for advanced use only).

        Returns
        -------
        A pandas table with the event info.

        """
        # do the plotting:
        result = self._call_adherer(dataset=self._dataset,
                                    function="compute_event_int_gaps", plot_show=False,

                                    id_colname=self._id_colname,
                                    event_date_colname=self._event_date_colname,
                                    event_duration_colname=self._event_duration_colname,
                                    event_daily_dose_colname=self._event_daily_dose_colname,
                                    medication_class_colname=self._medication_class_colname,

                                    carryover_within_obs_window=self._carryover_within_obs_window,
                                    carryover_into_obs_window=self._carryover_into_obs_window,
                                    carry_only_for_same_medication=\
                                        self._carry_only_for_same_medication,
                                    consider_dosage_change=self._consider_dosage_change,

                                    medication_change_means_new_treatment_episode=\
                                        self._medication_change_means_new_treatment_episode,
                                    maximum_permissible_gap=self._maximum_permissible_gap,
                                    maximum_permissible_gap_unit=self._maximum_permissible_gap_unit,

                                    followup_window_start_type=self._followup_window_start_type,
                                    followup_window_start=self._followup_window_start,
                                    followup_window_start_unit=self._followup_window_start_unit,
                                    followup_window_duration_type=\
                                        self._followup_window_duration_type,
                                    followup_window_duration=self._followup_window_duration,
                                    followup_window_duration_unit=\
                                        self._followup_window_duration_unit,

                                    observation_window_start_type=\
                                        self._observation_window_start_type,
                                    observation_window_start=self._observation_window_start,
                                    observation_window_start_unit=\
                                        self._observation_window_start_unit,
                                    observation_window_duration_type=\
                                        self._observation_window_duration_type,
                                    observation_window_duration=self._observation_window_duration,
                                    observation_window_duration_unit=\
                                        self._observation_window_duration_unit,

                                    sliding_window_start_type=self._sliding_window_start_type,
                                    sliding_window_start=self._sliding_window_start,
                                    sliding_window_start_unit=self._sliding_window_start_unit,
                                    sliding_window_duration_type=self._sliding_window_duration_type,
                                    sliding_window_duration=self._sliding_window_duration,
                                    sliding_window_duration_unit=self._sliding_window_duration_unit,
                                    sliding_window_step_duration_type=\
                                        self._sliding_window_step_duration_type,
                                    sliding_window_step_duration=self._sliding_window_step_duration,
                                    sliding_window_step_unit=self._sliding_window_step_unit,
                                    sliding_window_no_steps=self._sliding_window_no_steps,

                                    cma_to_apply=self._cma_to_apply,

                                    date_format=self._date_format,

                                    event_interval_colname=self._event_interval_colname,
                                    gap_days_colname=self._gap_days_colname,

                                    force_na_cma_for_failed_patients=\
                                        self._force_na_cma_for_failed_patients,
                                    keep_window_start_end_dates=self._keep_window_start_end_dates,
                                    remove_events_outside_followup_window=\
                                        self._remove_events_outside_followup_window,
                                    keep_event_interval_for_all_events=\
                                        self._keep_event_interval_for_all_events,

                                    parallel_backend=self._parallel_backend,
                                    parallel_threads=self._parallel_threads,

                                    suppress_warnings=self._suppress_warnings,
                                    save_event_info=self._save_event_info,

                                    na_symbol_numeric=self._na_symbol_numeric,
                                    na_symbol_string=self._na_symbol_string,
                                    logical_symbol_true=self._logical_symbol_true,
                                    logical_symbol_false=self._logical_symbol_false,
                                    colnames_dot_symbol=self._colnames_dot_symbol,
                                    colnames_start_dot=self._colnames_start_dot,

                                    path_to_rscript=get_rscript_path(),
                                    path_to_data_directory=get_data_sharing_directory(),
                                    print_adherer_messages=self._print_adherer_messages)

        # Were there errors?
        if result is None:
            raise CallAdhereRError('General computation error')
        elif result['return_code'] != 0:
            raise CallAdhereRError(result['message'])

        # Save the return code and message:
        self._computation_return_code = result['return_code']
        self._computation_messages = result['message']

        # Save the results:
        if 'EVENTINFO' in result:
            self._event_info = result['EVENTINFO']

        # Return the results:
        return self.get_event_info()


    def compute_treatment_episodes(self):
        """
        Compute treatment episodes (intended for advanced use only).

        Returns
        -------
        A pandas table with the treatment episodes.

        """
        # do the plotting:
        result = self._call_adherer(dataset=self._dataset,
                                    function="compute_treatment_episodes", plot_show=False,

                                    id_colname=self._id_colname,
                                    event_date_colname=self._event_date_colname,
                                    event_duration_colname=self._event_duration_colname,
                                    event_daily_dose_colname=self._event_daily_dose_colname,
                                    medication_class_colname=self._medication_class_colname,

                                    carryover_within_obs_window=self._carryover_within_obs_window,
                                    carryover_into_obs_window=self._carryover_into_obs_window,
                                    carry_only_for_same_medication=\
                                        self._carry_only_for_same_medication,
                                    consider_dosage_change=self._consider_dosage_change,

                                    medication_change_means_new_treatment_episode=\
                                        self._medication_change_means_new_treatment_episode,
                                    maximum_permissible_gap=self._maximum_permissible_gap,
                                    maximum_permissible_gap_unit=self._maximum_permissible_gap_unit,

                                    followup_window_start_type=self._followup_window_start_type,
                                    followup_window_start=self._followup_window_start,
                                    followup_window_start_unit=self._followup_window_start_unit,
                                    followup_window_duration_type=\
                                        self._followup_window_duration_type,
                                    followup_window_duration=self._followup_window_duration,
                                    followup_window_duration_unit=\
                                        self._followup_window_duration_unit,

                                    observation_window_start_type=\
                                        self._observation_window_start_type,
                                    observation_window_start=self._observation_window_start,
                                    observation_window_start_unit=\
                                        self._observation_window_start_unit,
                                    observation_window_duration_type=\
                                        self._observation_window_duration_type,
                                    observation_window_duration=self._observation_window_duration,
                                    observation_window_duration_unit=\
                                        self._observation_window_duration_unit,

                                    sliding_window_start_type=self._sliding_window_start_type,
                                    sliding_window_start=self._sliding_window_start,
                                    sliding_window_start_unit=self._sliding_window_start_unit,
                                    sliding_window_duration_type=self._sliding_window_duration_type,
                                    sliding_window_duration=self._sliding_window_duration,
                                    sliding_window_duration_unit=self._sliding_window_duration_unit,
                                    sliding_window_step_duration_type=\
                                        self._sliding_window_step_duration_type,
                                    sliding_window_step_duration=self._sliding_window_step_duration,
                                    sliding_window_step_unit=self._sliding_window_step_unit,
                                    sliding_window_no_steps=self._sliding_window_no_steps,

                                    cma_to_apply=self._cma_to_apply,

                                    date_format=self._date_format,

                                    event_interval_colname=self._event_interval_colname,
                                    gap_days_colname=self._gap_days_colname,

                                    force_na_cma_for_failed_patients=\
                                        self._force_na_cma_for_failed_patients,
                                    keep_window_start_end_dates=self._keep_window_start_end_dates,
                                    remove_events_outside_followup_window=\
                                        self._remove_events_outside_followup_window,
                                    keep_event_interval_for_all_events=\
                                        self._keep_event_interval_for_all_events,

                                    parallel_backend=self._parallel_backend,
                                    parallel_threads=self._parallel_threads,

                                    suppress_warnings=self._suppress_warnings,
                                    save_event_info=self._save_event_info,

                                    na_symbol_numeric=self._na_symbol_numeric,
                                    na_symbol_string=self._na_symbol_string,
                                    logical_symbol_true=self._logical_symbol_true,
                                    logical_symbol_false=self._logical_symbol_false,
                                    colnames_dot_symbol=self._colnames_dot_symbol,
                                    colnames_start_dot=self._colnames_start_dot,

                                    path_to_rscript=get_rscript_path(),
                                    path_to_data_directory=get_data_sharing_directory(),
                                    print_adherer_messages=self._print_adherer_messages)

        # Were there errors?
        if result is None:
            raise CallAdhereRError('General computation error')
        elif result['return_code'] != 0:
            raise CallAdhereRError(result['message'])

        # Save the return code and message:
        self._computation_return_code = result['return_code']
        self._computation_messages = result['message']

        # Save the results:
        if 'TREATMENTEPISODES' in result:
            self._treatment_episodes = result['TREATMENTEPISODES']

        # Return the results:
        return self.get_treatment_episodes()


    # Plotting:
    def plot(self,
             patients_to_plot=None,
             save_to=None,
             save_as='jpg',
             width=7,
             height=7,
             quality=90,
             dpi=150,
             duration=None,
             align_all_patients=False,
             align_first_event_at_zero=True,
             show_period='days',
             period_in_days=90,
             show_legend=True,
             legend_x='right',
             legend_y='bottom',
             legend_bkg_opacity=0.5,
             cex=1.0,
             cex_axis=0.75,
             cex_lab=1.0,
             show_cma=True,
             unspecified_category_label='drug',
             lty_event='solid',
             lwd_event=2,
             pch_start_event=15,
             pch_end_event=16,
             show_event_intervals=True,
             col_na='lightgray',
             col_continuation='black',
             lty_continuation='dotted',
             lwd_continuation=1,
             print_cma=True,
             plot_cma=True,
             plot_cma_as_histogram=True,
             cma_plot_ratio=0.10,
             cma_plot_col='lightgreen',
             cma_plot_border='darkgreen',
             cma_plot_bkg='aquamarine',
             cma_plot_text=None,
             highlight_followup_window=True,
             followup_window_col='green',
             highlight_observation_window=True,
             observation_window_col='yellow',
             observation_window_density=35,
             observation_window_angle=-30,
             show_real_obs_window_start=True,
             real_obs_window_density=35,
             real_obs_window_angle=30,
             bw_plot=False):
        """
        Plotting the CMA.

        Parameters
        ----------
        patients_to_plot : list
            the list of patients to plot (defaults to None = all patients)
        save_to : str
            The folder where to save the plots (defaults to None, i.e. same folder
            as the other results)
        save_as : str
            The format of the saved plot; can be 'jpg', 'png', 'tiff', 'eps' or
            'pdataset' (defaults to 'jpg')
        width : numeric
            Plot width in inches (defaults to 7)
        height : numeric
            Plot heght in inches (defaults to 7)
        quality : numeric
            Plot quality (applies only to certain formts; defaults to 90)
        dpi : numeric
            Plot resultion (applies only to certain formts; defaults to 150)
        patients_to_plot : strings
            The patient IDs to plot as a vector (defaults to None, i.e., all)
        duration : numeric
            Duration to plot in days (defaults to None, i.e., is determined
            from the data)
        align_all_patients : bool
            Alling all patients? (defaults to False)
        align_first_event_at_zero : bool
            If plot_align_all_patients == True, also place the event at the origin?
            (defaults to True)
        show_period : str
            Draw vertical bars at regular interval as dates or days; can be 'days'
            or 'dates' (defaults to 'days')
        period_in_days : numeric
            The interval (in days) at which to draw vertical guides (defaults to 90)
        show_legend : bool
            Show the legend? (defaults to True)
        legend_x : str or numeric
            Together with plot_legend_y specifies the position of the legend;
            can be 'left' or 'right' or a number; (defaults to 'right')
        legend_y : str or numeric
            Together with plot_legend_x specifies the position of the legend;
            can be 'bottom' or 'top' or a number; (defaults to 'bottom')
        legend_bkg_opacity : numeric
            The legend background opacity (between 0 and 1, defaults to 0.5)
        cex : numeric
            The relative text size (defaults to 1.0)
        cex_axis : numeric
            The relative axis text size (defaults to 0.75)
        cex_lab : numeric
            The relative labels text size (defaults to 1.0)
        show_cma : bool
            Show the CMA type? (defaults to True)
        unspecified_category_label : str
            The label of the unspecified category of medication (defaults to 'drug')
        lty_event : str
            Line style for plotting events; can be 'solid', 'dotted' or 'dashed'
            (defaults to 'solid')
        lwd_event : numeric
            Line width for plitting events (defaults to 2)
        pch_start_event : numeric
            Symbol for the event start; can be any of the R plotting symbols given at,
            for example, http://www.endmemo.com/program/R/pchsymbols.php (defaults to 15)
        pch_end_event : numeric
            Symbol for event end (see plot_pch_start_event for details; defaults to 16)
        show_event_intervals : bool
            Show the prescription intervals? (defaults to True)
        col_na : str
            The color of the missing data; can be any R color specification as,
            for example, given at http://www.stat.columbia.edu/~tzheng/files/Rcolor.pdataset
            (defaults to 'lightgray')
        col_continuation : str
            The color of the lines connections consecutive events (see plot_col_na
            for details; defaults to 'black')
        lty_continuation : str
            Style of the lines connections consecutive events (see plot_lty_event
            for details; defaults to 'dotted')
        lwd_continuation : numeric
            Line width for plitting events (defaults to 1)
        print_cma : bool
            Print CMA value next to the participant's ID? (defaults to True)
        plot_cma : bool
            Plot the CMA next to the participant ID? (defaults to True)
        plot_cma_as_histogram : bool
            Plot CMA as a histogram or as a density plot? (defaults to True)
        cma_plot_ratio : numeric
            The proportion of the total horizontal plot to be taken by the CMA plot
            (defaults to 0.10)
        cma_plot_col : str
            The color of the CMA plot (see plot_col_na for details; defaults to
            'lightgreen')
        cma_plot_border : str
            The color of the CMA border (see plot_col_na for details; defaults
            to 'darkgreen')
        cma_plot_bkg : str
            The color of the CMA background (see plot_col_na for details;
            defaults to 'darkgreen')
        cma_plot_text : str
            The color of the CMA text (see plot_col_na for details; defaults to
            None, i.e., the same as plot_cma_plot_border)
        highlight_followup_window : bool
            Highlight the follow-up window? (defaults to True)
        followup_window_col : str
            The color of the CMA follow-up window (see plot_col_na for details;
            defaults to 'green')
        highlight_observation_window : bool
            Highlight the observaion window? (defaults to True)
        observation_window_col : str
            The color of the CMA observation window (see plot_col_na for details;
            defaults to 'yellow')
        observation_window_density : numeric
            The density (per inch) of the hash lines marking the obervation window
            (defaults to 35)
        observation_window_angle : numeric
            The angle (in degrees) of the hash lines marking the obervation window
            (defaults to -30)
        show_real_obs_window_start : bool
            For some CMAs, the real observation window starts at a different date:
            should we show it? (defaults to True)
        real_obs_window_density : numeric
            Same as plot_observation_window_density (defaults to 35)
        real_obs_window_angle : numeric
            Same as plot_observation_window_angle (defaults to 30)
        bw_plot : bool
            If True, override all user-given colors and replace them with a scheme
            suitable for grayscale plotting (fedaults to False)

        Returns
        -------
        The resulting plot as a PIL.Image object.

        """
        # do the plotting:
        result = self._call_adherer(dataset=self._dataset,
                                    function=self._adherer_function, plot_show=True,

                                    id_colname=self._id_colname,
                                    event_date_colname=self._event_date_colname,
                                    event_duration_colname=self._event_duration_colname,
                                    event_daily_dose_colname=self._event_daily_dose_colname,
                                    medication_class_colname=self._medication_class_colname,

                                    carryover_within_obs_window=self._carryover_within_obs_window,
                                    carryover_into_obs_window=self._carryover_into_obs_window,
                                    carry_only_for_same_medication=\
                                        self._carry_only_for_same_medication,
                                    consider_dosage_change=self._consider_dosage_change,

                                    medication_change_means_new_treatment_episode=\
                                        self._medication_change_means_new_treatment_episode,
                                    maximum_permissible_gap=self._maximum_permissible_gap,
                                    maximum_permissible_gap_unit=self._maximum_permissible_gap_unit,

                                    followup_window_start_type=self._followup_window_start_type,
                                    followup_window_start=self._followup_window_start,
                                    followup_window_start_unit=self._followup_window_start_unit,
                                    followup_window_duration_type=\
                                        self._followup_window_duration_type,
                                    followup_window_duration=self._followup_window_duration,
                                    followup_window_duration_unit=\
                                        self._followup_window_duration_unit,

                                    observation_window_start_type=\
                                        self._observation_window_start_type,
                                    observation_window_start=self._observation_window_start,
                                    observation_window_start_unit=\
                                        self._observation_window_start_unit,
                                    observation_window_duration_type=\
                                        self._observation_window_duration_type,
                                    observation_window_duration=self._observation_window_duration,
                                    observation_window_duration_unit=\
                                        self._observation_window_duration_unit,

                                    sliding_window_start_type=self._sliding_window_start_type,
                                    sliding_window_start=self._sliding_window_start,
                                    sliding_window_start_unit=self._sliding_window_start_unit,
                                    sliding_window_duration_type=self._sliding_window_duration_type,
                                    sliding_window_duration=self._sliding_window_duration,
                                    sliding_window_duration_unit=self._sliding_window_duration_unit,
                                    sliding_window_step_duration_type=\
                                        self._sliding_window_step_duration_type,
                                    sliding_window_step_duration=self._sliding_window_step_duration,
                                    sliding_window_step_unit=self._sliding_window_step_unit,
                                    sliding_window_no_steps=self._sliding_window_no_steps,

                                    cma_to_apply=self._cma_to_apply,

                                    date_format=self._date_format,

                                    event_interval_colname=self._event_interval_colname,
                                    gap_days_colname=self._gap_days_colname,

                                    force_na_cma_for_failed_patients=\
                                        self._force_na_cma_for_failed_patients,
                                    keep_window_start_end_dates=self._keep_window_start_end_dates,
                                    remove_events_outside_followup_window=\
                                        self._remove_events_outside_followup_window,
                                    keep_event_interval_for_all_events=\
                                        self._keep_event_interval_for_all_events,

                                    parallel_backend=self._parallel_backend,
                                    parallel_threads=self._parallel_threads,

                                    suppress_warnings=self._suppress_warnings,
                                    save_event_info=self._save_event_info,

                                    na_symbol_numeric=self._na_symbol_numeric,
                                    na_symbol_string=self._na_symbol_string,
                                    logical_symbol_true=self._logical_symbol_true,
                                    logical_symbol_false=self._logical_symbol_false,
                                    colnames_dot_symbol=self._colnames_dot_symbol,
                                    colnames_start_dot=self._colnames_start_dot,

                                    plot_patients_to_plot=patients_to_plot,
                                    plot_save_to=save_to, plot_save_as=save_as,
                                    plot_width=width, plot_height=height,
                                    plot_quality=quality, plot_dpi=dpi,
                                    plot_duration=duration,
                                    plot_align_all_patients=align_all_patients,
                                    plot_align_first_event_at_zero=align_first_event_at_zero,
                                    plot_show_period=show_period,
                                    plot_period_in_days=period_in_days,
                                    plot_show_legend=show_legend,
                                    plot_legend_x=legend_x, plot_legend_y=legend_y,
                                    plot_legend_bkg_opacity=legend_bkg_opacity,
                                    plot_cex=cex, plot_cex_axis=cex_axis, plot_cex_lab=cex_lab,
                                    plot_show_cma=show_cma,
                                    plot_unspecified_category_label=unspecified_category_label,
                                    plot_lty_event=lty_event, plot_lwd_event=lwd_event,
                                    plot_pch_start_event=pch_start_event,
                                    plot_pch_end_event=pch_end_event,
                                    plot_show_event_intervals=show_event_intervals,
                                    plot_col_na=col_na,
                                    plot_col_continuation=col_continuation,
                                    plot_lty_continuation=lty_continuation,
                                    plot_lwd_continuation=lwd_continuation,
                                    plot_print_cma=print_cma, plot_plot_cma=plot_cma,
                                    plot_plot_cma_as_histogram=plot_cma_as_histogram,
                                    plot_cma_plot_ratio=cma_plot_ratio,
                                    plot_cma_plot_col=cma_plot_col,
                                    plot_cma_plot_border=cma_plot_border,
                                    plot_cma_plot_bkg=cma_plot_bkg,
                                    plot_cma_plot_text=cma_plot_text,
                                    plot_highlight_followup_window=highlight_followup_window,
                                    plot_followup_window_col=followup_window_col,
                                    plot_highlight_observation_window=highlight_observation_window,
                                    plot_observation_window_col=observation_window_col,
                                    plot_observation_window_density=observation_window_density,
                                    plot_observation_window_angle=observation_window_angle,
                                    plot_show_real_obs_window_start=show_real_obs_window_start,
                                    plot_real_obs_window_density=real_obs_window_density,
                                    plot_real_obs_window_angle=real_obs_window_angle,
                                    plot_bw_plot=bw_plot,

                                    path_to_rscript=get_rscript_path(),
                                    path_to_data_directory=get_data_sharing_directory(),
                                    print_adherer_messages=self._print_adherer_messages)

        # Were there errors?
        if result is None:
            raise CallAdhereRError('General plotting error')
        elif result['return_code'] != 0:
            raise CallAdhereRError(result['message'])

        # Save the return code and message:
        self._computation_return_code = result['return_code']
        self._computation_messages = result['message']

        # Return the plot:
        return result['plot']

    # Interactive plotting:
    def plot_interactive(self,
                         patient_to_plot=None # which patient to plot initially
                        ):
        """
        Interactive plotting.

        Parameters
        ----------
        patient_to_plot : str or numeric
            The patient ID to plot initially (defaults to None = 1st patient)

        Returns
        -------
        True if everything was OK.

        """
        # Some preliminary tests:
        if ((self._dataset is None) or
                (self._id_colname is None) or
                (self._event_date_colname is None) or
                (self._event_duration_colname is None)):
            warnings.warn('Interactive plotting of CMAs requires at a minimum '
                          'the dataset, id_colname, event_date_colname and '
                          'event_duration_colname to be defined.')
            return None

        # Do the interactive plotting:
        result = self._call_adherer(dataset=self._dataset, function='plot_interactive_cma',
                                    id_colname=self._id_colname,
                                    event_date_colname=self._event_date_colname,
                                    event_duration_colname=self._event_duration_colname,
                                    event_daily_dose_colname=self._event_daily_dose_colname,
                                    medication_class_colname=self._medication_class_colname,
                                    patient_to_plot=patient_to_plot)

        # Were there errors?
        if result is None:
            raise CallAdhereRError('General plotting error')
        elif result['return_code'] != 0:
            raise CallAdhereRError(result['message'])

        # Save the return code and message:
        self._computation_return_code = result['return_code']
        self._computation_messages = result['message']

        return True

    # The private workhorse function that really does everything
    @staticmethod
    def _call_adherer(dataset,
                      function,
                      id_colname,
                      event_date_colname,
                      event_duration_colname,
                      event_daily_dose_colname=None,
                      medication_class_colname=None,
                      carryover_within_obs_window=False,
                      carryover_into_obs_window=False,
                      carry_only_for_same_medication=False,
                      consider_dosage_change=False,
                      medication_change_means_new_treatment_episode=False,
                      maximum_permissible_gap=90,
                      maximum_permissible_gap_unit='days',
                      followup_window_start_type='numeric',
                      followup_window_start=0,
                      followup_window_start_unit='days',
                      followup_window_duration_type='numeric',
                      followup_window_duration=365*2,
                      followup_window_duration_unit='days',
                      observation_window_start_type='numeric',
                      observation_window_start=0,
                      observation_window_start_unit='days',
                      observation_window_duration_type='numeric',
                      observation_window_duration=365*2,
                      observation_window_duration_unit='days',
                      sliding_window_start_type='numeric',
                      sliding_window_start=0,
                      sliding_window_start_unit='days',
                      sliding_window_duration_type='numeric',
                      sliding_window_duration=90,
                      sliding_window_duration_unit='days',
                      sliding_window_step_duration_type='numeric',
                      sliding_window_step_duration=30,
                      sliding_window_step_unit='days',
                      sliding_window_no_steps=None,
                      cma_to_apply=None,
                      date_format='%m/%d/%Y',
                      event_interval_colname='event.interval',
                      gap_days_colname='gap.days',
                      force_na_cma_for_failed_patients=True,
                      keep_window_start_end_dates=False,
                      remove_events_outside_followup_window=True,
                      keep_event_interval_for_all_events=False,
                      parallel_backend='none',
                      parallel_threads='auto',
                      suppress_warnings=False,
                      save_event_info=False,
                      na_symbol_numeric='NA',
                      na_symbol_string='NA',
                      logical_symbol_true='TRUE',
                      logical_symbol_false='FALSE',
                      colnames_dot_symbol='.',
                      colnames_start_dot='.',
                      plot_show=False,
                      plot_save_to=None,
                      plot_save_as='jpg',
                      plot_width=7,
                      plot_height=7,
                      plot_quality=90,
                      plot_dpi=150,
                      plot_patients_to_plot=None,
                      plot_duration=None,
                      plot_align_all_patients=False,
                      plot_align_first_event_at_zero=True,
                      plot_show_period='days',
                      plot_period_in_days=90,
                      plot_show_legend=True,
                      plot_legend_x='right',
                      plot_legend_y='bottom',
                      plot_legend_bkg_opacity=0.5,
                      plot_cex=1.0,
                      plot_cex_axis=0.75,
                      plot_cex_lab=1.0,
                      plot_show_cma=True,
                      plot_unspecified_category_label='drug',
                      plot_lty_event='solid',
                      plot_lwd_event=2,
                      plot_pch_start_event=15,
                      plot_pch_end_event=16,
                      plot_show_event_intervals=True,
                      plot_col_na='lightgray',
                      plot_col_continuation='black',
                      plot_lty_continuation='dotted',
                      plot_lwd_continuation=1,
                      plot_print_cma=True,
                      plot_plot_cma=True,
                      plot_plot_cma_as_histogram=True,
                      plot_cma_plot_ratio=0.10,
                      plot_cma_plot_col='lightgreen',
                      plot_cma_plot_border='darkgreen',
                      plot_cma_plot_bkg='aquamarine',
                      plot_cma_plot_text=None,
                      plot_highlight_followup_window=True,
                      plot_followup_window_col='green',
                      plot_highlight_observation_window=True,
                      plot_observation_window_col='yellow',
                      plot_observation_window_density=35,
                      plot_observation_window_angle=-30,
                      plot_show_real_obs_window_start=True,
                      plot_real_obs_window_density=35,
                      plot_real_obs_window_angle=30,
                      plot_bw_plot=False,
                      patient_to_plot=None,
                      path_to_rscript=get_rscript_path(),
                      path_to_data_directory=get_data_sharing_directory(),
                      print_adherer_messages=True
                     ):
        """
        Call AdhereR.

        Call various functions exported by the R package AdhereR.
        Uses the 'shell' mechanism for portability and generality.

        Parameters
        ----------
        dataset : pandas.DataFrame
            The dataset on which AdhereR will work
        function : str
            The name of the AdhereR function to call
        id_colname : str
            The name of the column in dataset containing the patient IDs
        event_date_colname : str
            The name of the column in dataset containing the event dates
        event_duration_colname : str
            The name of the column in dataset containing the event duration
        event_daily_dose_colname : str
            The name of the column in dataset containing the event daily dose
            (defaults to None, i.e. undefined)
        medication_class_colname : str
            The name of the column in dataset containing the event medication
            type/class (defaults to None, i.e. undefined)
        carryover_within_obs_window : bool
            Carry over within the observaion window? (defaults to False)
        carryover_into_obs_window : bool
            Carry over into the observation window? (defaults to False)
        carry_only_for_same_medication : bool
            Carry only works only across same medication events? (defaults to
            False)
        consider_dosage_change : bool
            Consider dosage change? (defaults to False)
        medication_change_means_new_treatment_episode : bool
            Does a change in medication mean the start of a new episode?
            (defaults to False)
        maximum_permissible_gap : numeric
            The size of the maximum persimissible gap between episodes (in
            units; defaults to 180)
        maximum_permissible_gap_unit : str
            The unit of the maximum_permissible_gap; can be 'days', 'weeks',
            'months', 'years' or 'percent' (defaults to 'days')
        followup_window_start_type : str
            The follow-up window start unit; can be 'numeric' (default),
            'character' or 'date'
        followup_window_start : numeric, str, or date
            The follow-up window start; can be a number, a string or a date
        followup_window_start_unit : str
            The follow-up window start unit; can be 'days' (default), 'weeks',
            'months' or 'years'
        followup_window_duration_type : str
            The follow-up window duration unit; can be 'numeric' (default),
            'character' or 'date'
        followup_window_duration : numeric, str, or date
            The follow-up window duration; can be a number, a string or a date
        followup_window_duration_unit : str
            The follow-up window duration unit; can be 'days' (default),
            'weeks', 'months' or 'years'
        observation_window_start_type : str
            The observation window start unit; can be 'numeric' (default),
            'character' or 'date'
        observation_window_start : numeric, str, or date
            The observation window start; can be a number, a string or a date
        observation_window_start_unit : str
            The observation window start unit; can be 'days' (default), 'weeks',
            'months' or 'years'
        observation_window_duration_type : str
            The observation window duration unit; can be 'numeric' (default),
            'character' or 'date'
        observation_window_duration : numeric, str, or date
            The observation window duration; can be a number, a string or a date
        observation_window_duration_unit : str
            The observation window duration unit; can be 'days' (default),
            'weeks', 'months' or 'years'
        sliding_window_start_type : str
            The sliding window start unit; can be 'numeric' (default),
            'character' or 'date'
        sliding_window_start : numeric, str, or date
            The sliding window start; can be a number, a string or a date
        sliding_window_start_unit : str
            The sliding window start unit; can be 'days' (default), 'weeks',
            'months' or 'years'
        sliding_window_duration_type : str
            The sliding window duration unit; can be 'numeric' (default),
            'character' or 'date'
        sliding_window_duration : numeric, str, or date
            The sliding window duration; can be a number, a string or a date
        sliding_window_duration_unit : str
            The sliding window duration unit; can be 'days' (default), 'weeks',
            'months' or 'years'
        sliding_window_step_duration_type : str
            The sliding window step duration unit; can be 'numeric' (default)
            or 'character'
        sliding_window_step_duration : numeric or str
            The sliding window step duration; can be a number, a string or a date
        sliding_window_step_unit : str
            The sliding windowstep  duration unit; can be 'days' (default),
            'weeks', 'months' or 'years'
        sliding_window_no_steps : numeric
            The number of sliding windows (defaults to None, i.e., should use
            the duration and step instead)
        cma_to_apply : str
            CMA to apply for CMA_sliding_window and CMA_per_episode (defaults
            to None)
        date_format : str
            The date format to be used throughout the call (in the standard
            strftime() format)
        event_interval_colname : str
            What name to use for the internal column saving the event intervals
            (defaults to 'event.interval')
        gap_days_colname : str
            What name to use for the internal column saving the gap days
            (defaults to 'gap.days')
        force_na_cma_for_failed_patients : bool
            Force the patients that failed to missing CMA? (default to 'True')
        keep_window_start_end_dates : bool
            For compute_event_int_gaps: keep the window start and end dates?
            (defaults to False)
        remove_events_outside_followup_window : bool
            For compute_event_int_gaps: remove the events that fall outside the
            follow-up window? (defaults to True)
        keep_event_interval_for_all_events : bool
            For compute_event_int_gaps: keep the event interval for all event?
            (defaults to False)
        parallel_backend : str
            The parallel backend to use; can be 'none', 'multicore', 'snow',
            'snow(SOCK)', 'snow(MPI)', 'snow(NWS)' (defaults to 'none')
        parallel_threads : numeric or str
            Specification of the number of parallel threads; can be an actual
            number, 'auto' or a more complex list of nodes (defaults to 'auto').
            For example: "c(rep(list(list(host='user@remote-host',
            rscript=/usr/local/bin/Rscript,
            snowlib='/usr/local/lib64/R/library/')),2))" distributes computation
            to a Linux 'remote-host' (using passwordless ssh for user 'user') as
            two parallel threads
        suppress_warnings : bool
            Suppress the warnings produced by AdhereR? (default to False)
        save_event_info : bool
            Should the EVENTINFO be also saved?
        na_symbol_numeric : str
            The symbol used for missing data in numeric columns (defaults to 'NA')
        na_symbol_string : str
            The symbol used for missing data in string columns (defaults to 'NA')
        logical_symbol_true : str
            The symbol used for logical true (defaults to 'TRUE')
        logical_symbol_false : str
            The symbol used for logical true (defaults to 'FALSE')
        colnames_dot_symbol : str
            What symbol to replace the '.' in column names with (defaults to '.',
            i.e., no replacement)
        colnames_start_dot : str
            What symbol to replace the '.' begining a column names with (defaults
            to '.', i.e., no replacement)
        plot_show : bool
            Do the plotting? If true, also save the resulting dataset with a
            "-plotted" suffix to avoid overwriting previous results (defaults to False)
        plot_save_to : str
            The folder where to save the plots (defaults to None, i.e. same folder
            as the other results)
        plot_save_as : str
            The format of the saved plot; can be 'jpg', 'png', 'tiff', 'eps' or
            'pdataset' (defaults to 'jpg')
        plot_width : numeric
            Plot width in inches (defaults to 7)
        plot_height : numeric
            Plot heght in inches (defaults to 7)
        plot_quality : numeric
            Plot quality (applies only to certain formts; defaults to 90)
        plot_dpi : numeric
            Plot resultion (applies only to certain formts; defaults to 150)
        plot_patients_to_plot : strings
            The patient IDs to plot as a vector (defaults to None, i.e., all)
        plot_duration : numeric
            Duration to plot in days (defaults to None, i.e., is determined
            from the data)
        plot_align_all_patients : bool
            Alling all patients? (defaults to False)
        plot_align_first_event_at_zero : bool
            If plot_align_all_patients == True, also place the event at the origin?
            (defaults to True)
        plot_show_period : str
            Draw vertical bars at regular interval as dates or days; can be 'days'
            or 'dates' (defaults to 'days')
        plot_period_in_days : numeric
            The interval (in days) at which to draw vertical guides (defaults to 90)
        plot_show_legend : bool
            Show the legend? (defaults to True)
        plot_legend_x : str or numeric
            Together with plot_legend_y specifies the position of the legend;
            can be 'left' or 'right' or a number; (defaults to 'right')
        plot_legend_y : str or numeric
            Together with plot_legend_x specifies the position of the legend;
            can be 'bottom' or 'top' or a number; (defaults to 'bottom')
        plot_legend_bkg_opacity : numeric
            The legend background opacity (between 0 and 1, defaults to 0.5)
        plot_cex : numeric
            The relative text size (defaults to 1.0)
        plot_cex_axis : numeric
            The relative axis text size (defaults to 0.75)
        plot_cex_lab : numeric
            The relative labels text size (defaults to 1.0)
        plot_show_cma : bool
            Show the CMA type? (defaults to True)
        plot_unspecified_category_label : str
            The label of the unspecified category of medication (defaults to 'drug')
        plot_lty_event : str
            Line style for plotting events; can be 'solid', 'dotted' or 'dashed'
            (defaults to 'solid')
        plot_lwd_event : numeric
            Line width for plitting events (defaults to 2)
        plot_pch_start_event : numeric
            Symbol for the event start; can be any of the R plotting symbols given at,
            for example, http://www.endmemo.com/program/R/pchsymbols.php (defaults to 15)
        plot_pch_end_event : numeric
            Symbol for event end (see plot_pch_start_event for details; defaults to 16)
        plot_show_event_intervals : bool
            Show the prescription intervals? (defaults to True)
        plot_col_na : str
            The color of the missing data; can be any R color specification as,
            for example, given at http://www.stat.columbia.edu/~tzheng/files/Rcolor.pdataset
            (defaults to 'lightgray')
        plot_col_continuation : str
            The color of the lines connections consecutive events (see plot_col_na
            for details; defaults to 'black')
        plot_lty_continuation : str
            Style of the lines connections consecutive events (see plot_lty_event
            for details; defaults to 'dotted')
        plot_lwd_continuation : numeric
            Line width for plitting events (defaults to 1)
        plot_print_cma : bool
            Print CMA value next to the participant's ID? (defaults to True)
        plot_plot_cma : bool
            Plot the CMA next to the participant ID? (defaults to True)
        plot_plot_cma_as_histogram : bool
            Plot CMA as a histogram or as a density plot? (defaults to True)
        plot_cma_plot_ratio : numeric
            The proportion of the total horizontal plot to be taken by the CMA plot
            (defaults to 0.10)
        plot_cma_plot_col : str
            The color of the CMA plot (see plot_col_na for details; defaults to
            'lightgreen')
        plot_cma_plot_border : str
            The color of the CMA border (see plot_col_na for details; defaults
            to 'darkgreen')
        plot_cma_plot_bkg : str
            The color of the CMA background (see plot_col_na for details;
            defaults to 'darkgreen')
        plot_cma_plot_text : str
            The color of the CMA text (see plot_col_na for details; defaults to
            None, i.e., the same as plot_cma_plot_border)
        plot_highlight_followup_window : bool
            Highlight the follow-up window? (defaults to True)
        plot_followup_window_col : str
            The color of the CMA follow-up window (see plot_col_na for details;
            defaults to 'green')
        plot_highlight_observation_window : bool
            Highlight the observaion window? (defaults to True)
        plot_observation_window_col : str
            The color of the CMA observation window (see plot_col_na for details;
            defaults to 'yellow')
        plot_observation_window_density : numeric
            The density (per inch) of the hash lines marking the obervation window
            (defaults to 35)
        plot_observation_window_angle : numeric
            The angle (in degrees) of the hash lines marking the obervation window
            (defaults to -30)
        plot_show_real_obs_window_start : bool
            For some CMAs, the real observation window starts at a different date:
            should we show it? (defaults to True)
        plot_real_obs_window_density : numeric
            Same as plot_observation_window_density (defaults to 35)
        plot_real_obs_window_angle : numeric
            Same as plot_observation_window_angle (defaults to 30)
        plot_bw_plot : bool
            If True, override all user-given colors and replace them with a scheme
            suitable for grayscale plotting (fedaults to False)
        patient_to_plot : str
            The patient to plot in the interactive plotting (it can be interactively
            changed; deaults to None, i.e., the first patient)
        path_to_rscript : str
            The path to where Rscript is installed
        path_to_data_directory : str
            The path to the directory where the various data should be saved.
        print_adherer_messages : bool
            Print the AdhereR message (on top of returning them to the caller)?

        Returns
        -------
        Dictionary
            If a serious error has occured before being able to call AdhereR,
            returns None.
            Otherwise returns a dictionary containing various keys appropriate
            to the called function, as follows:
            - all:
                - return_code: numeric code returned by the shell call to AdhereR (0 = OK)
                - message: the string message returned by AdhereR (if any)
            - CMA1 .. CMA9, CMA_per_episode, CMA_sliding_window also return:
                - CMA: a pandas.Dataframe containing the computed CMAs
                - EVENTINFO: if explicitely requested (save_event_info == True),
                a pandas.Dataframe containing the event intervals and gaps

        """
        # Check that the Rscript and data sharing paths work:
        if not _check_r_package_ahderer_is_installed(path_to_rscript):
            warnings.warn('adhereR: Rscript is not given, not working or ' + \
                          'does not have the correct version of the AdhereR package.')
            return None
        if path_to_data_directory is None:
            warnings.warn('adhereR: the data sharing directory was not given.')
            return None

        # Check that dataset is of the right type and contains the required columns:
        if not isinstance(dataset, pandas.DataFrame):
            warnings.warn('adhereR: argument "dataset" must be a pandas DataFrame (or compatible).')
            return None
        if not function in ('CMA0',
                            'CMA1', 'CMA2', 'CMA3', 'CMA4',
                            'CMA5', 'CMA6', 'CMA7', 'CMA8', 'CMA9',
                            'plot_interactive_cma', 'CMA_per_episode', 'CMA_sliding_window',
                            'compute_event_int_gaps', 'compute_treatment_episodes'):
            warnings.warn('adhereR: argument "function" (' + function + ') is not a '
                          'known adhereR function".')
            return None
        if not id_colname in dataset.columns.values.tolist():
            warnings.warn('adhereR: argument "id_colname" (' + id_colname + ') must be '
                          'a column in "dataset".')
            return None
        if not event_date_colname in dataset.columns.values.tolist():
            warnings.warn('adhereR: argument "event_date_colname" (' +
                          event_date_colname + ') must be a column in "dataset".')
            return None
        if not event_duration_colname in dataset.columns.values.tolist():
            warnings.warn('adhereR: argument "event_duration_colname" (' +
                          event_duration_colname + ') must be a column in "dataset".')
            return None

        # Export the dataset:
        dataset.to_csv(os.path.join(path_to_data_directory, 'dataset.csv'),
                       sep='\t', na_rep='NA', header=True, index=False)

        # Create the parameters.log file:
        parameters_file = open(os.path.join(path_to_data_directory, 'parameters.log'), 'w+')
        # Write the parameters header:
        parameters_file.write('Parameters\n')

        # Write the parameters:

        # The function to call:
        parameters_file.write('function = "' + function + '"\n')


        # Required column names:
        parameters_file.write('ID.colname = "' + id_colname + '"\n')
        parameters_file.write('event.date.colname = "' + event_date_colname + '"\n')
        parameters_file.write('event.duration.colname = "' + event_duration_colname + '"\n')


        if (function in ('CMA5', 'CMA6', 'CMA7', 'CMA8', 'CMA9', 'plot_interactive_cma',
                         'CMA_per_episode', 'CMA_sliding_window')) and \
            ((event_daily_dose_colname is None) or (medication_class_colname is None)):
            warnings.warn('adhereR: argument "event_daily_dose_colname" and '
                          '"medication_class_colname" are required for CMA5-CMA9, '
                          'CMA_per_episode, CMA_sliding_window and plot_interactive_cma.')
            parameters_file.close()
            return None

        if event_daily_dose_colname is None:
            parameters_file.write('event.daily.dose.colname = ""\n')
        elif not event_daily_dose_colname in dataset.columns.values.tolist():
            warnings.warn('adhereR: argument "event_daily_dose_colname" (' +
                          event_daily_dose_colname + ') must be a column in "dataset".')
            return None
        else:
            parameters_file.write('event.daily.dose.colname = "' + event_daily_dose_colname + '"\n')
        if medication_class_colname is None:
            parameters_file.write('medication.class.colname = ""\n')
        elif not medication_class_colname in dataset.columns.values.tolist():
            warnings.warn('adhereR: argument "medication_class_colname" (' +
                          medication_class_colname + ') must be a column in "dataset".')
            return None
        else:
            parameters_file.write('medication.class.colname = "' + medication_class_colname + '"\n')


        if (function in ('CMA_per_episode', 'CMA_sliding_window')) and \
            not cma_to_apply in ('CMA1', 'CMA2', 'CMA3', 'CMA4', 'CMA5',
                                 'CMA6', 'CMA7', 'CMA8', 'CMA9'):
            warnings.warn('adhereR: argument "cma_to_apply" must be a valid simple '
                          'CMA for CMA_per_episode and CMA_sliding_window.')
            parameters_file.close()
            return None
        parameters_file.write('CMA.to.apply = "' + str(cma_to_apply) + '"\n')


        if not isinstance(carry_only_for_same_medication, bool):
            warnings.warn('adhereR: argument "carry_only_for_same_medication" '
                          'must be a bool.')
            parameters_file.close()
            return None
        parameters_file.write('carry.only.for.same.medication = "' +
                              ('TRUE' if carry_only_for_same_medication else 'FALSE') + '"\n')

        if not isinstance(consider_dosage_change, bool):
            warnings.warn('adhereR: argument "consider_dosage_change" must be a bool.')
            parameters_file.close()
            return None
        parameters_file.write('consider.dosage.change = "' +
                              ('TRUE' if consider_dosage_change else 'FALSE') + '"\n')

        if not isinstance(medication_change_means_new_treatment_episode, bool):
            warnings.warn('adhereR: argument "medication_change_means_new_treatment_episode" '
                          'must be a bool.')
            parameters_file.close()
            return None
        parameters_file.write('medication.change.means.new.treatment.episode = "' +
                              ('TRUE' if medication_change_means_new_treatment_episode else \
                               'FALSE') +
                              '"\n')

        if not isinstance(maximum_permissible_gap, numbers.Number) or maximum_permissible_gap <= 0:
            warnings.warn('adhereR: argument "maximum_permissible_gap" must be a '
                          'strictly positive number.')
            parameters_file.close()
            return None
        parameters_file.write('maximum.permissible.gap = "' + str(maximum_permissible_gap) + '"\n')

        if maximum_permissible_gap_unit not in ('days', 'weeks', 'months', 'years', 'percent'):
            warnings.warn('adhereR: argument "maximum_permissible_gap_unit" (' +
                          maximum_permissible_gap_unit + ') is not recognized.')
            parameters_file.close()
            return None
        parameters_file.write('maximum.permissible.gap.unit = "' +
                              maximum_permissible_gap_unit + '"\n')


        # Follow-up window:
        if followup_window_start_type not in ('numeric', 'character', 'date'):
            warnings.warn('adhereR: argument "followup_window_start_type" (' +
                          followup_window_start_type + ') is not recognized.')
            parameters_file.close()
            return None
        parameters_file.write('followup.window.start.type = "' + followup_window_start_type + '"\n')

        if isinstance(followup_window_start, numbers.Number):
            parameters_file.write('followup.window.start = "' + str(followup_window_start) + '"\n')
        elif isinstance(followup_window_start, (datetime.date, datetime.datetime)):
            parameters_file.write('followup.window.start = "' +
                                  followup_window_start.strftime(date_format) + '"\n')
        else:
            parameters_file.write('followup.window.start = "' + followup_window_start + '"\n')

        if followup_window_start_unit not in ('days', 'weeks', 'months', 'years'):
            warnings.warn('adhereR: argument "followup_window_start_unit" (' +
                          followup_window_start_unit + ') is not recognized.')
            parameters_file.close()
            return None
        parameters_file.write('followup.window.start.unit = "' +
                              followup_window_start_unit + '"\n')


        if followup_window_duration_type not in ('numeric', 'character', 'date'):
            warnings.warn('adhereR: argument "followup_window_duration_type" (' +
                          followup_window_duration_type + ') is not recognized.')
            parameters_file.close()
            return None
        parameters_file.write('followup.window.duration.type = "' +
                              followup_window_duration_type + '"\n')

        if isinstance(followup_window_duration, numbers.Number):
            parameters_file.write('followup.window.duration = "' +
                                  str(followup_window_duration) + '"\n')
        elif isinstance(followup_window_duration, (datetime.date, datetime.datetime)):
            parameters_file.write('followup.window.duration = "' +
                                  followup_window_duration.strftime(date_format) + '"\n')
        else:
            parameters_file.write('followup.window.duration = "' +
                                  followup_window_duration + '"\n')

        if followup_window_duration_unit not in ('days', 'weeks', 'months', 'years'):
            warnings.warn('adhereR: argument "followup_window_duration_unit" (' +
                          followup_window_duration_unit + ') is not recognized.')
            parameters_file.close()
            return None
        parameters_file.write('followup.window.duration.unit = "' +
                              followup_window_duration_unit + '"\n')


        # Observation window:
        if observation_window_start_type not in ('numeric', 'character', 'date'):
            warnings.warn('adhereR: argument "observation_window_start_type" (' +
                          observation_window_start_type + ') is not recognized.')
            parameters_file.close()
            return None
        parameters_file.write('observation.window.start.type = "' +
                              observation_window_start_type + '"\n')

        if isinstance(observation_window_start, numbers.Number):
            parameters_file.write('observation.window.start = "' +
                                  str(observation_window_start) + '"\n')
        elif isinstance(observation_window_start, (datetime.date, datetime.datetime)):
            parameters_file.write('observation.window.start = "' +
                                  observation_window_start.strftime(date_format) + '"\n')
        else:
            parameters_file.write('observation.window.start = "' +
                                  observation_window_start + '"\n')

        if observation_window_start_unit not in ('days', 'weeks', 'months', 'years'):
            warnings.warn('adhereR: argument "observation_window_start_unit" (' +
                          observation_window_start_unit + ') is not recognized.')
            parameters_file.close()
            return None
        parameters_file.write('observation.window.start.unit = "' +
                              observation_window_start_unit + '"\n')


        if observation_window_duration_type not in ('numeric', 'character', 'date'):
            warnings.warn('adhereR: argument "observation_window_duration_type" (' +
                          observation_window_duration_type + ') is not recognized.')
            parameters_file.close()
            return None
        parameters_file.write('observation.window.duration.type = "' +
                              observation_window_duration_type + '"\n')

        if isinstance(observation_window_duration, numbers.Number):
            parameters_file.write('observation.window.duration = "' +
                                  str(observation_window_duration) + '"\n')
        elif isinstance(observation_window_duration, (datetime.date, datetime.datetime)):
            parameters_file.write('observation.window.duration = "' +
                                  observation_window_duration.strftime(date_format) + '"\n')
        else:
            parameters_file.write('observation.window.duration = "' +
                                  observation_window_duration + '"\n')

        if observation_window_duration_unit not in ('days', 'weeks', 'months', 'years'):
            warnings.warn('adhereR: argument "observation_window_duration_unit" (' +
                          observation_window_duration_unit + ') is not recognized.')
            parameters_file.close()
            return None
        parameters_file.write('observation.window.duration.unit = "' +
                              observation_window_duration_unit + '"\n')


        # Sliding windows:
        if sliding_window_start_type not in ('numeric', 'character', 'date'):
            warnings.warn('adhereR: argument "sliding_window_start_type" (' +
                          sliding_window_start_type + ') is not recognized.')
            parameters_file.close()
            return None
        parameters_file.write('sliding.window.start.type = "' + sliding_window_start_type + '"\n')

        if isinstance(sliding_window_start, numbers.Number):
            parameters_file.write('sliding.window.start = "' + str(sliding_window_start) + '"\n')
        elif isinstance(sliding_window_start, (datetime.date, datetime.datetime)):
            parameters_file.write('sliding.window.start = "' +
                                  sliding_window_start.strftime(date_format) + '"\n')
        else:
            parameters_file.write('sliding.window.start = "' +
                                  sliding_window_start + '"\n')

        if sliding_window_start_unit not in ('days', 'weeks', 'months', 'years'):
            warnings.warn('adhereR: argument "sliding_window_start_unit" (' +
                          sliding_window_start_unit + ') is not recognized.')
            parameters_file.close()
            return None
        parameters_file.write('sliding.window.start.unit = "' +
                              sliding_window_start_unit + '"\n')


        if sliding_window_duration_type not in ('numeric', 'character', 'date'):
            warnings.warn('adhereR: argument "sliding_window_duration_type" (' +
                          sliding_window_duration_type + ') is not recognized.')
            parameters_file.close()
            return None
        parameters_file.write('sliding.window.duration.type = "' +
                              sliding_window_duration_type + '"\n')

        if isinstance(sliding_window_duration, numbers.Number):
            parameters_file.write('sliding.window.duration = "' +
                                  str(sliding_window_duration) + '"\n')
        elif isinstance(sliding_window_duration, (datetime.date, datetime.datetime)):
            parameters_file.write('sliding.window.duration = "' +
                                  sliding_window_duration.strftime(date_format) + '"\n')
        else:
            parameters_file.write('sliding.window.duration = "' +
                                  sliding_window_duration + '"\n')

        if sliding_window_duration_unit not in ('days', 'weeks', 'months', 'years'):
            warnings.warn('adhereR: argument "sliding_window_duration_unit" (' +
                          sliding_window_duration_unit + ') is not recognized.')
            parameters_file.close()
            return None
        parameters_file.write('sliding.window.duration.unit = "' +
                              sliding_window_duration_unit + '"\n')


        if sliding_window_step_duration_type not in ('numeric', 'character'):
            warnings.warn('adhereR: argument "sliding_window_step_duration_type" (' +
                          sliding_window_step_duration_type + ') is not recognized.')
            parameters_file.close()
            return None
        parameters_file.write('sliding.window.step.duration.type = "' +
                              sliding_window_step_duration_type + '"\n')

        if isinstance(sliding_window_step_duration, numbers.Number):
            parameters_file.write('sliding.window.step.duration = "' +
                                  str(sliding_window_step_duration) + '"\n')
        else:
            parameters_file.write('sliding.window.step.duration = "' +
                                  sliding_window_step_duration + '"\n')

        if sliding_window_step_unit not in ('days', 'weeks', 'months', 'years'):
            warnings.warn('adhereR: argument "sliding_window_step_unit" (' +
                          sliding_window_step_unit + ') is not recognized.')
            parameters_file.close()
            return None
        parameters_file.write('sliding.window.step.unit = "' + sliding_window_step_unit + '"\n')

        if isinstance(sliding_window_no_steps, numbers.Number):
            parameters_file.write('sliding.window.no.steps = "' +
                                  str(sliding_window_no_steps) + '"\n')
        elif sliding_window_no_steps is None:
            parameters_file.write('sliding.window.no.steps = "-1"\n')
        else:
            warnings.warn('adhereR: argument "sliding_window_no_steps" must '
                          'be a strictly positive number or None.')
            parameters_file.close()
            return None


        # Date format:
        if not isinstance(date_format, str):
            warnings.warn('adhereR: argument "date_format" must be a string '
                          'specifying a valid strftime() date.')
            parameters_file.close()
            return None
        parameters_file.write('date.format = "' + date_format + '"\n')


        # Auxiliary columns for event intervals computation:
        if not isinstance(event_interval_colname, str):
            warnings.warn('adhereR: argument "event_interval_colname" must be '
                          'a string specifying a valid column name.')
            parameters_file.close()
            return None
        parameters_file.write('event.interval.colname = "' + event_interval_colname + '"\n')

        if not isinstance(gap_days_colname, str):
            warnings.warn('adhereR: argument "gap_days_colname" must be a string '
                          'specifying a valid column name.')
            parameters_file.close()
            return None
        parameters_file.write('gap.days.colname = "' + gap_days_colname + '"\n')


        # compute_event_int_gaps arguments:
        if not isinstance(keep_window_start_end_dates, bool):
            warnings.warn('adhereR: argument "keep_window_start_end_dates" must be a bool.')
            parameters_file.close()
            return None
        parameters_file.write('keep.window.start.end.dates = "' +
                              ('TRUE' if keep_window_start_end_dates else 'FALSE') + '"\n')

        if not isinstance(remove_events_outside_followup_window, bool):
            warnings.warn('adhereR: argument "remove_events_outside_followup_window" '
                          'must be a bool.')
            parameters_file.close()
            return None
        parameters_file.write('remove.events.outside.followup.window = "' +
                              ('TRUE' if remove_events_outside_followup_window else 'FALSE') +
                              '"\n')

        if not isinstance(keep_event_interval_for_all_events, bool):
            warnings.warn('adhereR: argument "keep_event_interval_for_all_events" '
                          'must be a bool.')
            parameters_file.close()
            return None
        parameters_file.write('keep.event.interval.for.all.events = "' +
                              ('TRUE' if keep_event_interval_for_all_events else 'FALSE') +
                              '"\n')


        # compute_treatment_episodes arguments:
        if not isinstance(carryover_within_obs_window, bool):
            warnings.warn('adhereR: argument "carryover_within_obs_window" must be a bool.')
            parameters_file.close()
            return None
        parameters_file.write('carryover.within.obs.window = "' +
                              ('TRUE' if carryover_within_obs_window else 'FALSE') +
                              '"\n')

        if not isinstance(carryover_into_obs_window, bool):
            warnings.warn('adhereR: argument "carryover_into_obs_window" must be a bool.')
            parameters_file.close()
            return None
        parameters_file.write('carryover.into.obs.window = "' +
                              ('TRUE' if carryover_into_obs_window else 'FALSE') +
                              '"\n')



        # Parallel processing:
        if parallel_backend not in ('none', 'multicore', 'snow', 'snow(SOCK)',
                                    'snow(MPI)', 'snow(NWS)'):
            warnings.warn('adhereR: argument "parallel_backend" (' + parallel_backend +
                          ') is not recognized.')
            parameters_file.close()
            return None
        parameters_file.write('parallel.backend = "' + parallel_backend + '"\n')

        if isinstance(parallel_threads, numbers.Number):
            parameters_file.write('parallel.threads = "' + str(parallel_threads) + '"\n')
        else:
            parameters_file.write('parallel.threads = "' + parallel_threads + '"\n')


        # Other arguments:
        if not isinstance(force_na_cma_for_failed_patients, bool):
            warnings.warn('adhereR: argument "force_na_cma_for_failed_patients" must be a bool.')
            parameters_file.close()
            return None
        parameters_file.write('force.NA.CMA.for.failed.patients = "' +
                              ('TRUE' if force_na_cma_for_failed_patients else 'FALSE') +
                              '"\n')

        if not isinstance(suppress_warnings, bool):
            warnings.warn('adhereR: argument "suppress_warnings" must be a bool.')
            parameters_file.close()
            return None
        parameters_file.write('suppress.warnings = "' +
                              ('TRUE' if suppress_warnings else 'FALSE') +
                              '"\n')

        if not isinstance(save_event_info, bool):
            warnings.warn('adhereR: argument "save_event_info" must be a bool.')
            parameters_file.close()
            return None
        parameters_file.write('save.event.info = "' +
                              ('TRUE' if save_event_info else 'FALSE') +
                              '"\n')


        # Caller-specific conventions:
        if not isinstance(na_symbol_numeric, str):
            warnings.warn('adhereR: argument "save_event_info" must be a bool.')
            parameters_file.close()
            return None
        parameters_file.write('NA.SYMBOL.NUMERIC = "' + na_symbol_numeric + '"\n')

        if not isinstance(na_symbol_string, str):
            warnings.warn('adhereR: argument "save_event_info" must be a bool.')
            parameters_file.close()
            return None
        parameters_file.write('NA.SYMBOL.STRING = "' + na_symbol_string + '"\n')

        if not isinstance(logical_symbol_true, str):
            warnings.warn('adhereR: argument "save_event_info" must be a bool.')
            parameters_file.close()
            return None
        parameters_file.write('LOGICAL.SYMBOL.TRUE = "' + logical_symbol_true + '"\n')

        if not isinstance(logical_symbol_false, str):
            warnings.warn('adhereR: argument "save_event_info" must be a bool.')
            parameters_file.close()
            return None
        parameters_file.write('LOGICAL.SYMBOL.FALSE = "' + logical_symbol_false + '"\n')

        if not isinstance(colnames_dot_symbol, str):
            warnings.warn('adhereR: argument "save_event_info" must be a bool.')
            parameters_file.close()
            return None
        parameters_file.write('COLNAMES.DOT.SYMBOL = "' + colnames_dot_symbol + '"\n')

        if not isinstance(colnames_start_dot, str):
            warnings.warn('adhereR: argument "save_event_info" must be a bool.')
            parameters_file.close()
            return None
        parameters_file.write('COLNAMES.START.DOT = "' + colnames_start_dot + '"\n')


        # Plotting:
        if not isinstance(plot_show, bool):
            warnings.warn('adhereR: argument "plot_show" must be a bool.')
            parameters_file.close()
            return None
        parameters_file.write('plot.show = "' + ('TRUE' if plot_show else 'FALSE') + '"\n')

        if plot_save_to is None:
            parameters_file.write('plot.save.to = ""\n')
        elif isinstance(plot_save_to, str):
            parameters_file.write('plot.save.to = "' + plot_save_to + '"\n')
        else:
            warnings.warn('adhereR: argument "plot_save_to" must be a string or "None".')
            parameters_file.close()
            return None

        if plot_save_as not in ('jpg', 'png', 'tiff', 'eps', 'pdataset'):
            warnings.warn('adhereR: argument "plot_save_as" (' + plot_save_as +
                          ') is not recognized.')
            parameters_file.close()
            return None
        parameters_file.write('plot.save.as = "' + plot_save_as + '"\n')

        if not isinstance(plot_width, numbers.Number) or plot_width <= 0:
            warnings.warn('adhereR: argument "plot_width" must be a strictly positive number.')
            parameters_file.close()
            return None
        parameters_file.write('plot.width = "' + str(plot_width) + '"\n')

        if not isinstance(plot_height, numbers.Number) or plot_height <= 0:
            warnings.warn('adhereR: argument "plot_height" must be a strictly positive number.')
            parameters_file.close()
            return None
        parameters_file.write('plot.height = "' + str(plot_height) + '"\n')

        if not isinstance(plot_quality, numbers.Number) or plot_quality <= 0:
            warnings.warn('adhereR: argument "plot_quality" must be a strictly positive number.')
            parameters_file.close()
            return None
        parameters_file.write('plot.quality = "' + str(plot_quality) + '"\n')

        if not isinstance(plot_dpi, numbers.Number) or plot_dpi <= 0:
            warnings.warn('adhereR: argument "plot_dpi" must be a strictly positive number.')
            parameters_file.close()
            return None
        parameters_file.write('plot.dpi = "' + str(plot_dpi) + '"\n')

        if plot_patients_to_plot is None:
            parameters_file.write('plot.patients.to.plot = ""\n')
        elif isinstance(plot_patients_to_plot, list):
            parameters_file.write('plot.patients.to.plot = "' +
                                  (';'.join(str(x) for x in plot_patients_to_plot)) +
                                  '"\n')
        else:
            parameters_file.write('plot.patients.to.plot = "' + str(plot_patients_to_plot) + '"\n')

        if plot_duration is None:
            parameters_file.write('plot.duration = ""\n')
        elif isinstance(plot_duration, numbers.Number) and plot_duration > 0:
            parameters_file.write('plot.duration = "' + str(plot_duration) + '"\n')
        else:
            warnings.warn('adhereR: argument "plot_duration" must be a strictly positive number.')
            parameters_file.close()
            return None

        if not isinstance(plot_align_all_patients, bool):
            warnings.warn('adhereR: argument "plot_align_all_patients" must be a bool.')
            parameters_file.close()
            return None
        parameters_file.write('plot.align.all.patients = "' +
                              ('TRUE' if plot_align_all_patients else 'FALSE') +
                              '"\n')

        if not isinstance(plot_align_first_event_at_zero, bool):
            warnings.warn('adhereR: argument "plot_align_first_event_at_zero" must be a bool.')
            parameters_file.close()
            return None
        parameters_file.write('plot.align.first.event.at.zero = "' +
                              ('TRUE' if plot_align_first_event_at_zero else 'FALSE') +
                              '"\n')

        if plot_show_period not in ('days', 'dates'):
            warnings.warn('adhereR: argument "plot_show_period" (' +
                          plot_show_period + ') is not recognized.')
            parameters_file.close()
            return None
        parameters_file.write('plot.show.period = "' + plot_show_period + '"\n')

        if not isinstance(plot_period_in_days, numbers.Number) or plot_period_in_days <= 0:
            warnings.warn('adhereR: argument "plot_period_in_days" '
                          'must be a strictly positive number.')
            parameters_file.close()
            return None
        parameters_file.write('plot.period.in.days = "' + str(plot_period_in_days) + '"\n')

        if not isinstance(plot_show_legend, bool):
            warnings.warn('adhereR: argument "plot_show_legend" must be a bool.')
            parameters_file.close()
            return None
        parameters_file.write('plot.show.legend = "' +
                              ('TRUE' if plot_show_legend else 'FALSE') +
                              '"\n')

        if plot_legend_x in ('left', 'right') and plot_legend_y in ('bottom', 'top'):
            parameters_file.write('plot.legend.x = "' + plot_legend_x + '"\n')
            parameters_file.write('plot.legend.y = "' + plot_legend_y + '"\n')
        elif isinstance(plot_legend_x, numbers.Number) and \
             isinstance(plot_legend_y, numbers.Number) and \
             plot_legend_x >= 0 and plot_legend_y >= 0:
            parameters_file.write('plot.legend.x = "' + str(plot_legend_x) + '"\n')
            parameters_file.write('plot.legend.y = "' + str(plot_legend_y) + '"\n')
        else:
            warnings.warn('adhereR: argument "plot_legend_x" and '
                          '"plot_legend_y" are not recognized.')
            parameters_file.close()
            return None

        if not isinstance(plot_legend_bkg_opacity, numbers.Number) or \
           plot_legend_bkg_opacity < 0 or plot_legend_bkg_opacity > 1:
            warnings.warn('adhereR: argument "plot_legend_bkg_opacity" '
                          'must be a number between 0 and 1.')
            parameters_file.close()
            return None
        parameters_file.write('plot.legend.bkg.opacity = "' + str(plot_legend_bkg_opacity) + '"\n')

        if not isinstance(plot_cex, numbers.Number) or plot_cex < 0:
            warnings.warn('adhereR: argument "plot_cex" must be a strictly positive number.')
            parameters_file.close()
            return None
        parameters_file.write('plot.cex = "' + str(plot_cex) + '"\n')

        if not isinstance(plot_cex_axis, numbers.Number) or plot_cex_axis < 0:
            warnings.warn('adhereR: argument "plot_cex_axis" must be a strictly positive number.')
            parameters_file.close()
            return None
        parameters_file.write('plot.cex.axis = "' + str(plot_cex_axis) + '"\n')

        if not isinstance(plot_cex_lab, numbers.Number) or plot_cex_lab < 0:
            warnings.warn('adhereR: argument "plot_cex_lab" must be a strictly positive number.')
            parameters_file.close()
            return None
        parameters_file.write('plot.cex.lab = "' + str(plot_cex_lab) + '"\n')

        if not isinstance(plot_show_cma, bool):
            warnings.warn('adhereR: argument "plot_show_cma" must be a bool.')
            parameters_file.close()
            return None
        parameters_file.write('plot.show.cma = "' + ('TRUE' if plot_show_cma else 'FALSE') + '"\n')

        if not isinstance(plot_unspecified_category_label, str):
            warnings.warn('adhereR: argument "plot_unspecified_category_label" must be a string.')
            parameters_file.close()
            return None
        parameters_file.write('plot.unspecified.category.label = "' +
                              plot_unspecified_category_label + '"\n')

        if plot_lty_event not in ('solid', 'dotted', 'dashed'):
            warnings.warn('adhereR: argument "plot_lty_event" (' +
                          plot_lty_event + ') is not recognized.')
            parameters_file.close()
            return None
        parameters_file.write('plot.lty.event = "' + plot_lty_event + '"\n')

        if not isinstance(plot_lwd_event, numbers.Number) or plot_lwd_event < 0:
            warnings.warn('adhereR: argument "plot_lwd_event" must be a strictly positive number.')
            parameters_file.close()
            return None
        parameters_file.write('plot.lwd.event = "' + str(plot_lwd_event) + '"\n')

        if isinstance(plot_pch_start_event, numbers.Number):
            parameters_file.write('plot.pch.start.event = "' + str(plot_pch_start_event) + '"\n')
        elif isinstance(plot_pch_start_event, str):
            parameters_file.write('plot.pch.start.event = "' + plot_pch_start_event + '"\n')
        else:
            warnings.warn('adhereR: argument "plot_pch_start_event" is not recognized.')
            parameters_file.close()
            return None

        if isinstance(plot_pch_end_event, numbers.Number):
            parameters_file.write('plot.pch.end.event = "' + str(plot_pch_end_event) + '"\n')
        elif isinstance(plot_pch_end_event, str):
            parameters_file.write('plot.pch.end.event = "' + plot_pch_end_event + '"\n')
        else:
            warnings.warn('adhereR: argument "plot_pch_end_event" is not recognized.')
            parameters_file.close()
            return None

        if not isinstance(plot_show_event_intervals, bool):
            warnings.warn('adhereR: argument "plot_show_event_intervals" must be a bool.')
            parameters_file.close()
            return None
        parameters_file.write('plot.show.event.intervals = "' +
                              ('TRUE' if plot_show_event_intervals else 'FALSE') +
                              '"\n')

        if not isinstance(plot_col_na, str):
            warnings.warn('adhereR: argument "plot_col_na" must be a string.')
            parameters_file.close()
            return None
        parameters_file.write('plot.col.na = "' + plot_col_na + '"\n')

        if not isinstance(plot_col_continuation, str):
            warnings.warn('adhereR: argument "plot_col_continuation" must be a string.')
            parameters_file.close()
            return None
        parameters_file.write('plot.col.continuation = "' + plot_col_continuation + '"\n')

        if plot_lty_continuation not in ('solid', 'dotted', 'dashed'):
            warnings.warn('adhereR: argument "plot_lty_continuation" (' +
                          plot_lty_continuation + ') is not recognized.')
            parameters_file.close()
            return None
        parameters_file.write('plot.lty.continuation = "' + plot_lty_continuation + '"\n')

        if not isinstance(plot_lwd_continuation, numbers.Number) or plot_lwd_continuation < 0:
            warnings.warn('adhereR: argument "plot_lwd_continuation" '
                          'must be a strictly positive number.')
            parameters_file.close()
            return None
        parameters_file.write('plot.lwd.continuation = "' + str(plot_lwd_continuation) + '"\n')

        if not isinstance(plot_print_cma, bool):
            warnings.warn('adhereR: argument "plot_print_cma" must be a bool.')
            parameters_file.close()
            return None
        parameters_file.write('plot.print.CMA = "' +
                              ('TRUE' if plot_print_cma else 'FALSE') +
                              '"\n')

        if not isinstance(plot_plot_cma, bool):
            warnings.warn('adhereR: argument "plot_plot_cma" must be a bool.')
            parameters_file.close()
            return None
        parameters_file.write('plot.plot.CMA = "' + ('TRUE' if plot_plot_cma else 'FALSE') + '"\n')

        if not isinstance(plot_plot_cma_as_histogram, bool):
            warnings.warn('adhereR: argument "plot_plot_cma_as_histogram" must be a bool.')
            parameters_file.close()
            return None
        parameters_file.write('plot.plot.CMA.as.histogram = "' +
                              ('TRUE' if plot_plot_cma_as_histogram else 'FALSE') +
                              '"\n')

        if not isinstance(plot_cma_plot_ratio, numbers.Number) or \
           plot_cma_plot_ratio < 0 or plot_cma_plot_ratio > 1:
            warnings.warn('adhereR: argument "plot_cma_plot_ratio" '
                          'must be a number between 0 and 1.')
            parameters_file.close()
            return None
        parameters_file.write('plot.CMA.plot.ratio = "' + str(plot_cma_plot_ratio) + '"\n')

        if not isinstance(plot_cma_plot_col, str):
            warnings.warn('adhereR: argument "plot_cma_plot_col" must be a string.')
            parameters_file.close()
            return None
        parameters_file.write('plot.CMA.plot.col = "' + plot_cma_plot_col + '"\n')

        if not isinstance(plot_cma_plot_border, str):
            warnings.warn('adhereR: argument "plot_cma_plot_border" must be a string.')
            parameters_file.close()
            return None
        parameters_file.write('plot.CMA.plot.border = "' + plot_cma_plot_border + '"\n')

        if not isinstance(plot_cma_plot_bkg, str):
            warnings.warn('adhereR: argument "plot_cma_plot_bkg" must be a string.')
            parameters_file.close()
            return None
        parameters_file.write('plot.CMA.plot.bkg = "' + plot_cma_plot_bkg + '"\n')

        if plot_cma_plot_text is None:
            parameters_file.write('plot.CMA.plot.text = ""\n')
        elif not isinstance(plot_cma_plot_text, str):
            warnings.warn('adhereR: argument "plot_cma_plot_text" must be a string.')
            parameters_file.close()
            return None
        else:
            parameters_file.write('plot.CMA.plot.text = "' + plot_cma_plot_text + '"\n')

        if not isinstance(plot_highlight_followup_window, bool):
            warnings.warn('adhereR: argument "plot_highlight_followup_window" must be a bool.')
            parameters_file.close()
            return None
        parameters_file.write('plot.highlight.followup.window = "' +
                              ('TRUE' if plot_highlight_followup_window else 'FALSE') +
                              '"\n')

        if not isinstance(plot_followup_window_col, str):
            warnings.warn('adhereR: argument "plot_followup_window_col" must be a string.')
            parameters_file.close()
            return None
        parameters_file.write('plot.followup.window.col = "' + plot_followup_window_col + '"\n')

        if not isinstance(plot_highlight_observation_window, bool):
            warnings.warn('adhereR: argument "plot_highlight_observation_window" must be a bool.')
            parameters_file.close()
            return None
        parameters_file.write('plot.highlight.observation.window = "' +
                              ('TRUE' if plot_highlight_observation_window else 'FALSE') +
                              '"\n')

        if not isinstance(plot_observation_window_col, str):
            warnings.warn('adhereR: argument "plot_observation_window_col" must be a string.')
            parameters_file.close()
            return None
        parameters_file.write('plot.observation.window.col = "' +
                              plot_observation_window_col + '"\n')

        if not isinstance(plot_observation_window_density, numbers.Number) or \
           plot_observation_window_density < 0:
            warnings.warn('adhereR: argument "plot_observation_window_density" '
                          'must be a positive number.')
            parameters_file.close()
            return None
        parameters_file.write('plot.observation.window.density = "' +
                              str(plot_observation_window_density) + '"\n')

        if not isinstance(plot_observation_window_angle, numbers.Number):
            warnings.warn('adhereR: argument "plot_observation_window_angle" '
                          'must be a positive number.')
            parameters_file.close()
            return None
        parameters_file.write('plot.observation.window.angle = "' +
                              str(plot_observation_window_angle) + '"\n')

        if not isinstance(plot_show_real_obs_window_start, bool):
            warnings.warn('adhereR: argument "plot_show_real_obs_window_start" must be a bool.')
            parameters_file.close()
            return None
        parameters_file.write('plot.show.real.obs.window.start = "' +
                              ('TRUE' if plot_show_real_obs_window_start else 'FALSE') + '"\n')

        if not isinstance(plot_real_obs_window_density, numbers.Number) or \
           plot_real_obs_window_density < 0:
            warnings.warn('adhereR: argument "plot_real_obs_window_density" '
                          'must be a positive number.')
            parameters_file.close()
            return None
        parameters_file.write('plot.real.obs.window.density = "' +
                              str(plot_real_obs_window_density) + '"\n')

        if not isinstance(plot_real_obs_window_angle, numbers.Number):
            warnings.warn('adhereR: argument "plot_real_obs_window_angle" must '
                          'be a positive number.')
            parameters_file.close()
            return None
        parameters_file.write('plot.real.obs.window.angle = "' +
                              str(plot_real_obs_window_angle) + '"\n')

        if not isinstance(plot_bw_plot, bool):
            warnings.warn('adhereR: argument "plot_bw_plot" must be a bool.')
            parameters_file.close()
            return None
        parameters_file.write('plot.bw.plot = "' + ('TRUE' if plot_bw_plot else 'FALSE') + '"\n')

        if patient_to_plot is None:
            parameters_file.write('patient_to_plot = ""\n')
        elif isinstance(patient_to_plot, str):
            parameters_file.write('patient_to_plot = "' + patient_to_plot + '"\n')
        elif isinstance(patient_to_plot, numbers.Number):
            parameters_file.write('patient_to_plot = "' + str(patient_to_plot) + '"\n')
        else:
            warnings.warn('adhereR: argument "patient_to_plot" must be None or a valid patient ID.')
            parameters_file.close()
            return None


        # Write the parameters ending:
        parameters_file.write('end_parameters\n')
        # Close the parameters file:
        parameters_file.close()

        # Remove any pre-existing results file:
        try:
            os.remove(path_to_data_directory + "/Adherer-results.txt")
        except OSError:
            pass

        # Call adhereR:
        rscript_cmd = '"' + path_to_rscript + '"' + ' --vanilla -e ' + \
                      '"library(' + _R_PACKAGE_NAME + '); ' + \
                      _R_PACKAGE_EXTERNAL_CALL_FUNCTION + \
                      '(\'' + path_to_data_directory.replace('\\', '\\\\') + '\')"'
        return_code = subprocess.call(rscript_cmd, shell=True)

        if return_code != 0:
            warnings.warn('adhereR: some error has occured when calling AdhereR (code ' +
                          str(return_code) + '): ".')
            return None

        # Check and load the results:
        with open(os.path.join(path_to_data_directory,
                               "Adherer-results.txt"), 'r') as adherer_messages_file:
            adherer_messages = adherer_messages_file.readlines()
            adherer_messages_file.close()
        if print_adherer_messages:
            print('Adherer returned code ' + str(return_code) +
                  ' and said:\n' + ''.join(adherer_messages))
        if adherer_messages[-1][0:3] != 'OK:':
            warnings.warn('adhereR: some error has occured when calling AdhereR (code ' +
                          str(return_code) + '): "' + ''.join(adherer_messages) + '".')
            return None

        # The return value (as a dictionary 'name':'value')
        ret_val = {'return_code':return_code,
                   'message':adherer_messages}

        if function in ('CMA1', 'CMA2', 'CMA3', 'CMA4', 'CMA5', 'CMA6', 'CMA7',
                        'CMA8', 'CMA9', 'CMA_per_episode', 'CMA_sliding_window'):
            # Expecting CMA.csv and possibly EVENTINFO.csv
            ret_val['CMA'] = pandas.read_csv(os.path.join(path_to_data_directory,
                                                          'CMA' +
                                                          ('-plotted' if plot_show else '') +
                                                          '.csv'), sep='\t', header=0)
            if save_event_info:
                ret_val['EVENTINFO'] = pandas.read_csv(os.path.join(path_to_data_directory,
                                                                    'EVENTINFO' +
                                                                    ('-plotted'
                                                                     if plot_show else
                                                                     '') +
                                                                    '.csv'), sep='\t', header=0)
        elif function == 'plot_interactive_cma':
            # Expecting nothing really...
            pass
        elif function == 'compute_event_int_gaps':
            # Expecting EVENTINFO.csv only:
            ret_val['EVENTINFO'] = pandas.read_csv(os.path.join(path_to_data_directory,
                                                                'EVENTINFO.csv'),
                                                   sep='\t', header=0)
        elif function == 'compute_treatment_episodes':
            # Expect TREATMENTEPISODES.csv:
            ret_val['TREATMENTEPISODES'] = pandas.read_csv(os.path.join(path_to_data_directory,
                                                                        'TREATMENTEPISODES.csv'),
                                                           sep='\t', header=0)

        if (plot_show is True) and (function != 'plot_interactive_cma'):
            # Load the produced image (if any):
            ret_val['plot'] = Image.open(os.path.join((plot_save_to
                                                       if not (plot_save_to is None) else
                                                       path_to_data_directory),
                                                      'adherer-plot' + '.' + plot_save_as))

        # Everything seems fine....
        return ret_val



class CMA1(CMA0):
    """
    CMA1 class
    """

    # What CMA class ("function") is this?:
    _adherer_function = 'CMA1'

    def __init__(self,
                 dataset,
                 id_colname,
                 event_date_colname,
                 event_duration_colname,
                 followup_window_start_type='numeric',
                 followup_window_start=0,
                 followup_window_start_unit='days',
                 followup_window_duration_type='numeric',
                 followup_window_duration=365*2,
                 followup_window_duration_unit='days',
                 observation_window_start_type='numeric',
                 observation_window_start=0,
                 observation_window_start_unit='days',
                 observation_window_duration_type='numeric',
                 observation_window_duration=365*2,
                 observation_window_duration_unit='days',
                 date_format='%m/%d/%Y',
                 event_interval_colname='event.interval',
                 gap_days_colname='gap.days',
                 force_na_cma_for_failed_patients=True,
                 parallel_backend='none',
                 parallel_threads='auto',
                 suppress_warnings=False,
                 save_event_info=False,
                 na_symbol_numeric='NA',
                 na_symbol_string='NA',
                 logical_symbol_true='TRUE',
                 logical_symbol_false='FALSE',
                 colnames_dot_symbol='.',
                 colnames_start_dot='.',
                 path_to_rscript=get_rscript_path(),
                 path_to_data_directory=get_data_sharing_directory(),
                 print_adherer_messages=True):

        # Call the base class constructor:
        super().__init__(dataset=dataset,
                         id_colname=id_colname,
                         event_date_colname=event_date_colname,
                         event_duration_colname=event_duration_colname,
                         followup_window_start_type=followup_window_start_type,
                         followup_window_start=followup_window_start,
                         followup_window_start_unit=followup_window_start_unit,
                         followup_window_duration_type=followup_window_duration_type,
                         followup_window_duration=followup_window_duration,
                         followup_window_duration_unit=followup_window_duration_unit,
                         observation_window_start_type=observation_window_start_type,
                         observation_window_start=observation_window_start,
                         observation_window_start_unit=observation_window_start_unit,
                         observation_window_duration_type=observation_window_duration_type,
                         observation_window_duration=observation_window_duration,
                         observation_window_duration_unit=observation_window_duration_unit,
                         date_format=date_format,
                         event_interval_colname=event_interval_colname,
                         gap_days_colname=gap_days_colname,
                         force_na_cma_for_failed_patients=force_na_cma_for_failed_patients,
                         parallel_backend=parallel_backend,
                         parallel_threads=parallel_threads,
                         suppress_warnings=suppress_warnings,
                         save_event_info=save_event_info,
                         na_symbol_numeric=na_symbol_numeric,
                         na_symbol_string=na_symbol_string,
                         logical_symbol_true=logical_symbol_true,
                         logical_symbol_false=logical_symbol_false,
                         colnames_dot_symbol=colnames_dot_symbol,
                         colnames_start_dot=colnames_start_dot,
                         path_to_rscript=path_to_rscript,
                         path_to_data_directory=path_to_data_directory,
                         print_adherer_messages=print_adherer_messages)

        # Compute the CMA:
        result = super()._call_adherer(function=self._adherer_function,
                                       dataset=self._dataset,
                                       id_colname=self._id_colname,
                                       event_date_colname=self._event_date_colname,
                                       event_duration_colname=self._event_duration_colname,
                                       followup_window_start_type=self._followup_window_start_type,
                                       followup_window_start=self._followup_window_start,
                                       followup_window_start_unit=self._followup_window_start_unit,
                                       followup_window_duration_type=\
                                           self._followup_window_duration_type,
                                       followup_window_duration=self._followup_window_duration,
                                       followup_window_duration_unit=\
                                           self._followup_window_duration_unit,
                                       observation_window_start_type=\
                                           self._observation_window_start_type,
                                       observation_window_start=self._observation_window_start,
                                       observation_window_start_unit=\
                                           self._observation_window_start_unit,
                                       observation_window_duration_type=\
                                           self._observation_window_duration_type,
                                       observation_window_duration=\
                                           self._observation_window_duration,
                                       observation_window_duration_unit=\
                                           self._observation_window_duration_unit,
                                       date_format=self._date_format,
                                       event_interval_colname=self._event_interval_colname,
                                       gap_days_colname=self._gap_days_colname,
                                       force_na_cma_for_failed_patients=\
                                           self._force_na_cma_for_failed_patients,
                                       parallel_backend=self._parallel_backend,
                                       parallel_threads=self._parallel_threads,
                                       suppress_warnings=self._suppress_warnings,
                                       save_event_info=self._save_event_info,
                                       na_symbol_numeric=self._na_symbol_numeric,
                                       na_symbol_string=self._na_symbol_string,
                                       logical_symbol_true=self._logical_symbol_true,
                                       logical_symbol_false=self._logical_symbol_false,
                                       colnames_dot_symbol=self._colnames_dot_symbol,
                                       colnames_start_dot=self._colnames_start_dot,
                                       path_to_rscript=path_to_rscript,
                                       path_to_data_directory=path_to_data_directory,
                                       print_adherer_messages=self._print_adherer_messages)

        # Were there errors?
        if result is None:
            raise CallAdhereRError('General computing error')
        elif result['return_code'] != 0:
            raise CallAdhereRError(result['message'])

        # Save the return code and message:
        self._computation_return_code = result['return_code']
        self._computation_messages = result['message']

        # Save the results:
        self._cma = result['CMA']
        if 'EVENTINFO' in result:
            self._event_info = result['EVENTINFO']



class CMA2(CMA1):
    """
    CMA2 class
    """

    # What CMA class ("function") is this?:
    _adherer_function = 'CMA2'



class CMA3(CMA1):
    """
    CMA3 class
    """

    # What CMA class ("function") is this?:
    _adherer_function = 'CMA3'



class CMA4(CMA1):
    """
    CMA4 class
    """

    # What CMA class ("function") is this?:
    _adherer_function = 'CMA4'



class CMA5(CMA0):
    """
    CMA5 class
    """

    # What CMA class ("function") is this?:
    _adherer_function = 'CMA5'

    def __init__(self,
                 dataset,
                 id_colname,
                 event_date_colname,
                 event_duration_colname,
                 event_daily_dose_colname,
                 medication_class_colname,
                 carry_only_for_same_medication=False,
                 consider_dosage_change=False,
                 followup_window_start_type='numeric',
                 followup_window_start=0,
                 followup_window_start_unit='days',
                 followup_window_duration_type='numeric',
                 followup_window_duration=365*2,
                 followup_window_duration_unit='days',
                 observation_window_start_type='numeric',
                 observation_window_start=0,
                 observation_window_start_unit='days',
                 observation_window_duration_type='numeric',
                 observation_window_duration=365*2,
                 observation_window_duration_unit='days',
                 date_format='%m/%d/%Y',
                 event_interval_colname='event.interval',
                 gap_days_colname='gap.days',
                 force_na_cma_for_failed_patients=True,
                 parallel_backend='none',
                 parallel_threads='auto',
                 suppress_warnings=False,
                 save_event_info=False,
                 na_symbol_numeric='NA',
                 na_symbol_string='NA',
                 logical_symbol_true='TRUE',
                 logical_symbol_false='FALSE',
                 colnames_dot_symbol='.',
                 colnames_start_dot='.',
                 path_to_rscript=get_rscript_path(),
                 path_to_data_directory=get_data_sharing_directory(),
                 print_adherer_messages=True):

        # Call the base class constructor:
        super().__init__(dataset=dataset,
                         id_colname=id_colname,
                         event_date_colname=event_date_colname,
                         event_duration_colname=event_duration_colname,
                         event_daily_dose_colname=event_daily_dose_colname,
                         medication_class_colname=medication_class_colname,
                         carry_only_for_same_medication=carry_only_for_same_medication,
                         consider_dosage_change=consider_dosage_change,
                         followup_window_start_type=followup_window_start_type,
                         followup_window_start=followup_window_start,
                         followup_window_start_unit=followup_window_start_unit,
                         followup_window_duration_type=followup_window_duration_type,
                         followup_window_duration=followup_window_duration,
                         followup_window_duration_unit=followup_window_duration_unit,
                         observation_window_start_type=observation_window_start_type,
                         observation_window_start=observation_window_start,
                         observation_window_start_unit=observation_window_start_unit,
                         observation_window_duration_type=observation_window_duration_type,
                         observation_window_duration=observation_window_duration,
                         observation_window_duration_unit=observation_window_duration_unit,
                         date_format=date_format,
                         event_interval_colname=event_interval_colname,
                         gap_days_colname=gap_days_colname,
                         force_na_cma_for_failed_patients=force_na_cma_for_failed_patients,
                         parallel_backend=parallel_backend,
                         parallel_threads=parallel_threads,
                         suppress_warnings=suppress_warnings,
                         save_event_info=save_event_info,
                         na_symbol_numeric=na_symbol_numeric,
                         na_symbol_string=na_symbol_string,
                         logical_symbol_true=logical_symbol_true,
                         logical_symbol_false=logical_symbol_false,
                         colnames_dot_symbol=colnames_dot_symbol,
                         colnames_start_dot=colnames_start_dot,
                         path_to_rscript=path_to_rscript,
                         path_to_data_directory=path_to_data_directory,
                         print_adherer_messages=print_adherer_messages)

        # Compute the CMA:
        result = super()._call_adherer(function=self._adherer_function,
                                       dataset=self._dataset,
                                       id_colname=self._id_colname,
                                       event_date_colname=self._event_date_colname,
                                       event_duration_colname=self._event_duration_colname,
                                       event_daily_dose_colname=self._event_daily_dose_colname,
                                       medication_class_colname=self._medication_class_colname,
                                       carry_only_for_same_medication=\
                                           self._carry_only_for_same_medication,
                                       consider_dosage_change=self._consider_dosage_change,
                                       followup_window_start_type=self._followup_window_start_type,
                                       followup_window_start=self._followup_window_start,
                                       followup_window_start_unit=self._followup_window_start_unit,
                                       followup_window_duration_type=\
                                           self._followup_window_duration_type,
                                       followup_window_duration=self._followup_window_duration,
                                       followup_window_duration_unit=\
                                           self._followup_window_duration_unit,
                                       observation_window_start_type=\
                                           self._observation_window_start_type,
                                       observation_window_start=self._observation_window_start,
                                       observation_window_start_unit=\
                                           self._observation_window_start_unit,
                                       observation_window_duration_type=\
                                           self._observation_window_duration_type,
                                       observation_window_duration=\
                                           self._observation_window_duration,
                                       observation_window_duration_unit=\
                                           self._observation_window_duration_unit,
                                       date_format=self._date_format,
                                       event_interval_colname=self._event_interval_colname,
                                       gap_days_colname=self._gap_days_colname,
                                       force_na_cma_for_failed_patients=\
                                           self._force_na_cma_for_failed_patients,
                                       parallel_backend=self._parallel_backend,
                                       parallel_threads=self._parallel_threads,
                                       suppress_warnings=self._suppress_warnings,
                                       save_event_info=self._save_event_info,
                                       na_symbol_numeric=self._na_symbol_numeric,
                                       na_symbol_string=self._na_symbol_string,
                                       logical_symbol_true=self._logical_symbol_true,
                                       logical_symbol_false=self._logical_symbol_false,
                                       colnames_dot_symbol=self._colnames_dot_symbol,
                                       colnames_start_dot=self._colnames_start_dot,
                                       path_to_rscript=path_to_rscript,
                                       path_to_data_directory=path_to_data_directory,
                                       print_adherer_messages=self._print_adherer_messages)

        # Were there errors?
        if result is None:
            raise CallAdhereRError('General computing error')
        elif result['return_code'] != 0:
            raise CallAdhereRError(result['message'])

        # Save the return code and message:
        self._computation_return_code = result['return_code']
        self._computation_messages = result['message']

        # Save the results:
        self._cma = result['CMA']
        if 'EVENTINFO' in result:
            self._event_info = result['EVENTINFO']



class CMA6(CMA5):
    """
    CMA6 class
    """

    # What CMA class ("function") is this?:
    _adherer_function = 'CMA6'



class CMA7(CMA5):
    """
    CMA7 class
    """

    # What CMA class ("function") is this?:
    _adherer_function = 'CMA7'



class CMA8(CMA5):
    """
    CMA8 class
    """

    # What CMA class ("function") is this?:
    _adherer_function = 'CMA8'



class CMA9(CMA5):
    """
    CMA9 class
    """

    # What CMA class ("function") is this?:
    _adherer_function = 'CMA9'



class CMAPerEpisode(CMA0):
    """
    CMAPerEpisode class
    """

    # What CMA class ("function") is this?:
    _adherer_function = 'CMA_per_episode'

    def __init__(self,
                 dataset,
                 cma_to_apply,
                 id_colname,
                 event_date_colname,
                 event_duration_colname,
                 event_daily_dose_colname,
                 medication_class_colname,
                 carry_only_for_same_medication=False,
                 consider_dosage_change=False,
                 medication_change_means_new_treatment_episode=False,
                 maximum_permissible_gap=90,
                 maximum_permissible_gap_unit='days',
                 followup_window_start_type='numeric',
                 followup_window_start=0,
                 followup_window_start_unit='days',
                 followup_window_duration_type='numeric',
                 followup_window_duration=365*2,
                 followup_window_duration_unit='days',
                 observation_window_start_type='numeric',
                 observation_window_start=0,
                 observation_window_start_unit='days',
                 observation_window_duration_type='numeric',
                 observation_window_duration=365*2,
                 observation_window_duration_unit='days',
                 date_format='%m/%d/%Y',
                 event_interval_colname='event.interval',
                 gap_days_colname='gap.days',
                 force_na_cma_for_failed_patients=True,
                 parallel_backend='none',
                 parallel_threads='auto',
                 suppress_warnings=False,
                 save_event_info=False,
                 na_symbol_numeric='NA',
                 na_symbol_string='NA',
                 logical_symbol_true='TRUE',
                 logical_symbol_false='FALSE',
                 colnames_dot_symbol='.',
                 colnames_start_dot='.',
                 path_to_rscript=get_rscript_path(),
                 path_to_data_directory=get_data_sharing_directory(),
                 print_adherer_messages=True):

        # Call the base class constructor:
        super().__init__(dataset=dataset,
                         id_colname=id_colname,
                         event_date_colname=event_date_colname,
                         event_duration_colname=event_duration_colname,
                         event_daily_dose_colname=event_daily_dose_colname,
                         medication_class_colname=medication_class_colname,
                         carry_only_for_same_medication=carry_only_for_same_medication,
                         consider_dosage_change=consider_dosage_change,
                         medication_change_means_new_treatment_episode=\
                             medication_change_means_new_treatment_episode,
                         maximum_permissible_gap=maximum_permissible_gap,
                         maximum_permissible_gap_unit=maximum_permissible_gap_unit,
                         followup_window_start_type=followup_window_start_type,
                         followup_window_start=followup_window_start,
                         followup_window_start_unit=followup_window_start_unit,
                         followup_window_duration_type=followup_window_duration_type,
                         followup_window_duration=followup_window_duration,
                         followup_window_duration_unit=followup_window_duration_unit,
                         observation_window_start_type=observation_window_start_type,
                         observation_window_start=observation_window_start,
                         observation_window_start_unit=observation_window_start_unit,
                         observation_window_duration_type=observation_window_duration_type,
                         observation_window_duration=observation_window_duration,
                         observation_window_duration_unit=observation_window_duration_unit,
                         cma_to_apply=cma_to_apply,
                         date_format=date_format,
                         event_interval_colname=event_interval_colname,
                         gap_days_colname=gap_days_colname,
                         force_na_cma_for_failed_patients=force_na_cma_for_failed_patients,
                         parallel_backend=parallel_backend,
                         parallel_threads=parallel_threads,
                         suppress_warnings=suppress_warnings,
                         save_event_info=save_event_info,
                         na_symbol_numeric=na_symbol_numeric,
                         na_symbol_string=na_symbol_string,
                         logical_symbol_true=logical_symbol_true,
                         logical_symbol_false=logical_symbol_false,
                         colnames_dot_symbol=colnames_dot_symbol,
                         colnames_start_dot=colnames_start_dot,
                         path_to_rscript=path_to_rscript,
                         path_to_data_directory=path_to_data_directory,
                         print_adherer_messages=print_adherer_messages)

        # Compute the CMA:
        result = super()._call_adherer(function=self._adherer_function,
                                       dataset=self._dataset,
                                       id_colname=self._id_colname,
                                       event_date_colname=self._event_date_colname,
                                       event_duration_colname=self._event_duration_colname,
                                       event_daily_dose_colname=self._event_daily_dose_colname,
                                       medication_class_colname=self._medication_class_colname,
                                       carry_only_for_same_medication=\
                                           self._carry_only_for_same_medication,
                                       consider_dosage_change=self._consider_dosage_change,
                                       medication_change_means_new_treatment_episode=\
                                           self._medication_change_means_new_treatment_episode,
                                       maximum_permissible_gap=self._maximum_permissible_gap,
                                       maximum_permissible_gap_unit=\
                                           self._maximum_permissible_gap_unit,
                                       followup_window_start_type=self._followup_window_start_type,
                                       followup_window_start=self._followup_window_start,
                                       followup_window_start_unit=self._followup_window_start_unit,
                                       followup_window_duration_type=\
                                           self._followup_window_duration_type,
                                       followup_window_duration=self._followup_window_duration,
                                       followup_window_duration_unit=\
                                           self._followup_window_duration_unit,
                                       observation_window_start_type=\
                                           self._observation_window_start_type,
                                       observation_window_start=self._observation_window_start,
                                       observation_window_start_unit=\
                                           self._observation_window_start_unit,
                                       observation_window_duration_type=\
                                           self._observation_window_duration_type,
                                       observation_window_duration=\
                                           self._observation_window_duration,
                                       observation_window_duration_unit=\
                                           self._observation_window_duration_unit,
                                       cma_to_apply=self._cma_to_apply,
                                       date_format=self._date_format,
                                       event_interval_colname=self._event_interval_colname,
                                       gap_days_colname=self._gap_days_colname,
                                       force_na_cma_for_failed_patients=\
                                           self._force_na_cma_for_failed_patients,
                                       parallel_backend=self._parallel_backend,
                                       parallel_threads=self._parallel_threads,
                                       suppress_warnings=self._suppress_warnings,
                                       save_event_info=self._save_event_info,
                                       na_symbol_numeric=self._na_symbol_numeric,
                                       na_symbol_string=self._na_symbol_string,
                                       logical_symbol_true=self._logical_symbol_true,
                                       logical_symbol_false=self._logical_symbol_false,
                                       colnames_dot_symbol=self._colnames_dot_symbol,
                                       colnames_start_dot=self._colnames_start_dot,
                                       path_to_rscript=path_to_rscript,
                                       path_to_data_directory=path_to_data_directory,
                                       print_adherer_messages=self._print_adherer_messages)

        # Were there errors?
        if result is None:
            raise CallAdhereRError('General computing error')
        elif result['return_code'] != 0:
            raise CallAdhereRError(result['message'])

        # Save the return code and message:
        self._computation_return_code = result['return_code']
        self._computation_messages = result['message']

        # Save the results:
        self._cma = result['CMA']
        if 'EVENTINFO' in result:
            self._event_info = result['EVENTINFO']



class CMASlidingWindow(CMA0):
    """
    CMASlidingWindow class
    """

    # What CMA class ("function") is this?:
    _adherer_function = 'CMA_sliding_window'

    def __init__(self,
                 dataset,
                 cma_to_apply,
                 id_colname,
                 event_date_colname,
                 event_duration_colname,
                 event_daily_dose_colname,
                 medication_class_colname,
                 carry_only_for_same_medication=False,
                 consider_dosage_change=False,
                 followup_window_start_type='numeric',
                 followup_window_start=0,
                 followup_window_start_unit='days',
                 followup_window_duration_type='numeric',
                 followup_window_duration=365*2,
                 followup_window_duration_unit='days',
                 observation_window_start_type='numeric',
                 observation_window_start=0,
                 observation_window_start_unit='days',
                 observation_window_duration_type='numeric',
                 observation_window_duration=365*2,
                 observation_window_duration_unit='days',
                 sliding_window_start_type='numeric',
                 sliding_window_start=0,
                 sliding_window_start_unit='days',
                 sliding_window_duration_type='numeric',
                 sliding_window_duration=90,
                 sliding_window_duration_unit='days',
                 sliding_window_step_duration_type='numeric',
                 sliding_window_step_duration=30,
                 sliding_window_step_unit='days',
                 sliding_window_no_steps=None,
                 date_format='%m/%d/%Y',
                 event_interval_colname='event.interval',
                 gap_days_colname='gap.days',
                 force_na_cma_for_failed_patients=True,
                 parallel_backend='none',
                 parallel_threads='auto',
                 suppress_warnings=False,
                 save_event_info=False,
                 na_symbol_numeric='NA',
                 na_symbol_string='NA',
                 logical_symbol_true='TRUE',
                 logical_symbol_false='FALSE',
                 colnames_dot_symbol='.',
                 colnames_start_dot='.',
                 path_to_rscript=get_rscript_path(),
                 path_to_data_directory=get_data_sharing_directory(),
                 print_adherer_messages=True):

        # Call the base class constructor:
        super().__init__(dataset=dataset,
                         id_colname=id_colname,
                         event_date_colname=event_date_colname,
                         event_duration_colname=event_duration_colname,
                         event_daily_dose_colname=event_daily_dose_colname,
                         medication_class_colname=medication_class_colname,
                         carry_only_for_same_medication=carry_only_for_same_medication,
                         consider_dosage_change=consider_dosage_change,
                         followup_window_start_type=followup_window_start_type,
                         followup_window_start=followup_window_start,
                         followup_window_start_unit=followup_window_start_unit,
                         followup_window_duration_type=followup_window_duration_type,
                         followup_window_duration=followup_window_duration,
                         followup_window_duration_unit=followup_window_duration_unit,
                         observation_window_start_type=observation_window_start_type,
                         observation_window_start=observation_window_start,
                         observation_window_start_unit=observation_window_start_unit,
                         observation_window_duration_type=observation_window_duration_type,
                         observation_window_duration=observation_window_duration,
                         observation_window_duration_unit=observation_window_duration_unit,
                         sliding_window_start_type=sliding_window_start_type,
                         sliding_window_start=sliding_window_start,
                         sliding_window_start_unit=sliding_window_start_unit,
                         sliding_window_duration_type=sliding_window_duration_type,
                         sliding_window_duration=sliding_window_duration,
                         sliding_window_duration_unit=sliding_window_duration_unit,
                         sliding_window_step_duration_type=sliding_window_step_duration_type,
                         sliding_window_step_duration=sliding_window_step_duration,
                         sliding_window_step_unit=sliding_window_step_unit,
                         sliding_window_no_steps=sliding_window_no_steps,
                         cma_to_apply=cma_to_apply,
                         date_format=date_format,
                         event_interval_colname=event_interval_colname,
                         gap_days_colname=gap_days_colname,
                         force_na_cma_for_failed_patients=force_na_cma_for_failed_patients,
                         parallel_backend=parallel_backend,
                         parallel_threads=parallel_threads,
                         suppress_warnings=suppress_warnings,
                         save_event_info=save_event_info,
                         na_symbol_numeric=na_symbol_numeric,
                         na_symbol_string=na_symbol_string,
                         logical_symbol_true=logical_symbol_true,
                         logical_symbol_false=logical_symbol_false,
                         colnames_dot_symbol=colnames_dot_symbol,
                         colnames_start_dot=colnames_start_dot,
                         path_to_rscript=path_to_rscript,
                         path_to_data_directory=path_to_data_directory,
                         print_adherer_messages=print_adherer_messages)

        # Compute the CMA:
        result = super()._call_adherer(function=self._adherer_function,
                                       dataset=self._dataset,
                                       id_colname=self._id_colname,
                                       event_date_colname=self._event_date_colname,
                                       event_duration_colname=self._event_duration_colname,
                                       event_daily_dose_colname=self._event_daily_dose_colname,
                                       medication_class_colname=self._medication_class_colname,
                                       carry_only_for_same_medication=\
                                           self._carry_only_for_same_medication,
                                       consider_dosage_change=self._consider_dosage_change,
                                       followup_window_start_type=self._followup_window_start_type,
                                       followup_window_start=self._followup_window_start,
                                       followup_window_start_unit=self._followup_window_start_unit,
                                       followup_window_duration_type=\
                                           self._followup_window_duration_type,
                                       followup_window_duration=self._followup_window_duration,
                                       followup_window_duration_unit=\
                                           self._followup_window_duration_unit,
                                       observation_window_start_type=\
                                           self._observation_window_start_type,
                                       observation_window_start=self._observation_window_start,
                                       observation_window_start_unit=\
                                           self._observation_window_start_unit,
                                       observation_window_duration_type=\
                                           self._observation_window_duration_type,
                                       observation_window_duration=\
                                           self._observation_window_duration,
                                       observation_window_duration_unit=\
                                           self._observation_window_duration_unit,
                                       sliding_window_start_type=self._sliding_window_start_type,
                                       sliding_window_start=self._sliding_window_start,
                                       sliding_window_start_unit=self._sliding_window_start_unit,
                                       sliding_window_duration_type=\
                                           self._sliding_window_duration_type,
                                       sliding_window_duration=self._sliding_window_duration,
                                       sliding_window_duration_unit=\
                                           self._sliding_window_duration_unit,
                                       sliding_window_step_duration_type=\
                                           self._sliding_window_step_duration_type,
                                       sliding_window_step_duration=\
                                           self._sliding_window_step_duration,
                                       sliding_window_step_unit=self._sliding_window_step_unit,
                                       sliding_window_no_steps=self._sliding_window_no_steps,
                                       cma_to_apply=self._cma_to_apply,
                                       date_format=self._date_format,
                                       event_interval_colname=self._event_interval_colname,
                                       gap_days_colname=self._gap_days_colname,
                                       force_na_cma_for_failed_patients=\
                                           self._force_na_cma_for_failed_patients,
                                       parallel_backend=self._parallel_backend,
                                       parallel_threads=self._parallel_threads,
                                       suppress_warnings=self._suppress_warnings,
                                       save_event_info=self._save_event_info,
                                       na_symbol_numeric=self._na_symbol_numeric,
                                       na_symbol_string=self._na_symbol_string,
                                       logical_symbol_true=self._logical_symbol_true,
                                       logical_symbol_false=self._logical_symbol_false,
                                       colnames_dot_symbol=self._colnames_dot_symbol,
                                       colnames_start_dot=self._colnames_start_dot,
                                       path_to_rscript=path_to_rscript,
                                       path_to_data_directory=path_to_data_directory,
                                       print_adherer_messages=self._print_adherer_messages)

        # Were there errors?
        if result is None:
            raise CallAdhereRError('General computing error')
        elif result['return_code'] != 0:
            raise CallAdhereRError(result['message'])

        # Save the return code and message:
        self._computation_return_code = result['return_code']
        self._computation_messages = result['message']

        # Save the results:
        self._cma = result['CMA']
        if 'EVENTINFO' in result:
            self._event_info = result['EVENTINFO']
