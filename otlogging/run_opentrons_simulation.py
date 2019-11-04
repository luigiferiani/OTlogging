#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re
import sys
import argparse
from pprint import pprint
from opentrons import simulate


def is_summary_command(_command):
    return _command['level'] == 0


def is_moving_liquid_command(_command):
    """Returns True if command contains both a source and a destination"""
    _has_source_and_dest = ('source' in _command['payload'] and
                            'dest'   in _command['payload'])
    return _has_source_and_dest


def get_slot_and_well_name(_in, pipette_type):
    """
    Returns a tuple of (slot, well_name).
    If using a multichannel pipette, it expands the columns into wells or a tuple"""
    _rows = 'ABCDEFGH'
    if isinstance(_in, tuple):
        _in = _in[0]
    _in_slot = _in.get_parent().get_parent().get_name()
    _in_name = _in.get_name()
    if pipette_type == 'multi' and _in_name.startswith('A'):
        # find column name. If regex fails, return the whole well name
        re_out = re.findall(r'\d+$', _in_name)
        if len(re_out) == 0:
            raise ValueError('Regex failed: cannot find a number at the end of the well name??')
        _col = re_out[0]
        # expand column into 8 wells
        _in_names = []
        _in_slots = []
        for _row in _rows:
            _in_names.append(_row+_col)
            _in_slots.append(_in_slot)
        return _in_slots, _in_names
    else:
        return [_in_slot], [_in_name]


def is_trough(_command):
    # we already know source is not a list
    _loc = _command['payload']['source']
    if isinstance(_loc, list):
        is_trough_by_well = [is_well_from_trough(x) for x in _loc]
        if all(is_trough_by_well):
            return True
        elif not any(is_trough_by_well):
            return False
        else:
            raise ValueError('some wells in source are from trough but not all. Not coded for this case')
    else:
        return is_well_from_trough(_loc)


def is_well_from_trough(_loc):
    if isinstance(_loc, tuple):
        _loc = _loc[0]
    if 'trough' in _loc.get_parent().get_name():
        return True
    else:
        return False


def get_pipette_type(_command):
    return _command['payload']['instrument'].type


def get_volume(_command):
    return [_command['payload']['volume']]


def which_transfer_case(_command):
    """
    Returns one of the following:
        'trough_to_many':
            source is not a list and it's the trough, destination is a list
        'one_to_many':
            source is not a list but not the trough, destination is a list
        'many_to_many'
            both source and destination are lists, source is not trough
        'one_to_one'
            neither source and destination are lists, source is not trough
    """
    # 4 cases now really:
    # - we are dispensing water from the trough
    # - it's a proper one-to-many command,
    # - it's a many-to-many command, (using a well_series object)
    # - it's a one-to-one command, (if using a single tip pipette e.g.)
    _payload = _command['payload']
    if is_trough(_command):
        if (_payload['source'].__class__.__name__ not in ['list','WellSeries']) and (_payload['dest'].__class__.__name__ in ['list','WellSeries']):
            case = 'trough-to-many'
        else:
            pprint(_command)
            # import pdb; pdb.set_trace()
            raise ValueError('Trough involved in command that is not one-to-many: Not a supported command yet!')
    else:
        if (not isinstance(_payload['source'],list)) and isinstance(_payload['dest'],list):
            case = 'one-to-many'
        elif all(isinstance(_payload[k],list) for k in ['source', 'dest']):
            case = 'many-to-many'
        elif not any(isinstance(_payload[k],list) for k in ['source', 'dest']):
            case = 'one-to-one'
        else:
            raise ValueError('sth fishy here')
    return case


def process_one2many(_command, _fidout):
    pipette_type = get_pipette_type(_command)
    _payload = _command['payload']
    src_slot, src_name = get_slot_and_well_name(_payload['source'], pipette_type)
    amount = get_volume(_command)
    # loop on dest only
    for dst in _payload['dest']:
        # unpack tuples (well, height) and get slot and name
        dst_slot, dst_name = get_slot_and_well_name(dst,pipette_type)
        # print
        print_mapping(src_slot, src_name, dst_slot, dst_name, amount, _fidout)
        # print_mapping(src_slot, src_name, dst_slot, dst_name)


def process_many2many(_command, _fidout):
    pipette_type = get_pipette_type(_command)
    _payload = _command['payload']
    amount = get_volume(_command)
    # loop on both source and dest
    for src, dst in zip(_payload['source'], _payload['dest']):
        # unpack tuples (well, height) and get slot and name
        src_slot, src_name = get_slot_and_well_name(src, pipette_type)
        dst_slot, dst_name = get_slot_and_well_name(dst, pipette_type)
        # print
        print_mapping(src_slot, src_name, dst_slot, dst_name, amount, _fidout)
        # print_mapping(src_slot, src_name, dst_slot, dst_name)


def process_one2one(_command, _fidout):
    pipette_type = get_pipette_type(_command)
    _payload = _command['payload']
    # unpack tuples (well, height) and get slot and name
    src_slot, src_name = get_slot_and_well_name(_payload['source'], pipette_type)
    dst_slot, dst_name = get_slot_and_well_name(_payload['dest'], pipette_type)
    amount = get_volume(_command)
    # print
    print_mapping(src_slot, src_name, dst_slot, dst_name, amount, _fidout)
    # print_mapping(src_slot, src_name, dst_slot, dst_name)


def print_mapping(_src_slot, _src_name, _dst_slot, _dst_name, _amount, _fidout):
    if len(_amount)==1 and len(_amount)!=len(_dst_name):
        _amount = _amount*len(_dst_name)
    try:
        for _sslt, _snm, _dslt, _dnm, _amnt in zip(
                _src_slot, _src_name, _dst_slot, _dst_name, _amount):
            print('{},{},{},{},{:.1f}'.format(_sslt, _snm, _dslt, _dnm, _amnt),
                  file=_fidout)
    except:
        import pdb; pdb.set_trace()


def write_header(_fidout):
    print(','.join(['source_slot', 'source_well', 'dest_slot', 'dest_well', 'volume']),
          file=_fidout)


def main():

    parser = argparse.ArgumentParser(
        description="Run a robot's simulation, output well mapping in csv-friendly format"
    )
    parser.add_argument('protocol',
                        type=str)
    parser.add_argument('-o', '--output',
                        type=argparse.FileType('w'),
                        default=sys.stdout)

    args = parser.parse_args()
    protocol_fname = args.protocol
    fidout = args.output

    with open(protocol_fname,'r') as fid:
        robot_log = simulate.simulate(fid)

    # pprint(robot_log)
    write_header(fidout)
    # loop on command log
    for command in robot_log:
        # extract info from the summary level, so discard all commands not at level 0
        if not is_summary_command(command):
            continue

        # discard commands not involving moving liquid: need source and destination
        if not is_moving_liquid_command(command):
            continue

        case = which_transfer_case(command)
        # 4 cases now atm:
        # - we are dispensing water from the trough
        # - it's a proper one-to-many command,
        # - it's a many-to-many command, (using a well_series object)
        # - it's a one-to-one command, (if using a single tip pipette e.g.)
        if case == 'trough-to-many':
            # ignore trough to many
            pass
        elif case == 'one-to-many':
            process_one2many(command, fidout)
        elif case == 'many-to-many':
            process_many2many(command, fidout)
        elif case == 'one-to-one':
            process_one2one(command, fidout)
        else:
            pass

#%%
if __name__ == '__main__':
    main()
