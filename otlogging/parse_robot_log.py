#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re
import sys
import argparse
from collections import namedtuple

LINE_TYPES = {'aspirate':'Aspirating',
              'dispense':'Dispensing',
              'pickup':'Picking up',
              'droptip':'Dropping'}

AMOUNT_ASPIRATED = r"(?<=Aspirating\ )\w*\.\w*(?=\ uL\ from)"
AMOUNT_DISPENSED = r"(?<=Dispensing\ )\w*\.\w*(?=\ uL\ into)"
SOURCE_WELL      = r"(?<=from\ well\ )[A-Z]*\d*(?=\ in\ )"
DEST_WELL        = r"(?<=into\ well\ )[A-Z]*\d*(?=\ in\ )"
DECK_SLOT        = r"(?<=\ in\ \")\d*(?=\")"

Source = namedtuple('Source', 'slot well amount')
Dest = namedtuple('Dest', 'slot well amount')
OutLine = namedtuple('OutLine', 'source_slot, source_well, dest_slot, dest_well, amount')

def which_type_of_line(raw_line, linetypes_dict):
    """
    Reads the line, returns whether it contains:
        - Aspirate
        - Dispense
        - Pick up tip(s)
        - Drop tip
    """
    # print(raw_line)
    _line = raw_line.strip()
    _line_type = [k for k,v in linetypes_dict.items() if v in _line]
    # return None if line doesn't match
    if len(_line_type) == 0:
        return
    else:
        _line_type = _line_type[0]
    return _line_type


class LiquidTransfer(object):
    """
    transfer can be:
        1 aspirate -> 1 dispense
        N aspirate -> 1 dispense (I won't support this at the moment, if the aspirate are from different wells)
        1 aspirate -> N dispense
    what closes a transfer?
        a) drop tip
        b) an aspirate after a dispense
    what starts a transfer?
        a) a pick up
        b) an aspirate after a dispense
    pick up is always after a drop (or beginning of protocol)
    """
    def __init__(self, _line, _line_type, pipette_type=None):
        self.source = []
        self.dest = []
        self.is_closed = False
        self.pipette_type = ''
        self.last_action_type = ''
        if _line_type is 'aspirate':
            assert pipette_type is not None, 'A pipette_type must be provided'
            self.pipette_type = pipette_type
            self._update_source(_line)
            self.last_action_type = _line_type
        elif _line_type is 'pickup':
            assert pipette_type is None, 'When built by pick_up, do not give pipette_type'
            self.set_pipette_type(_line)
            self.last_action_type = _line_type
        else:
            raise Exception('Object can be built only with aspirate and pickup.')

    def set_pipette_type(self, _line):
        if 'tip wells' in _line:
            self.pipette_type = 'multi'
        elif 'tip well ' in _line:
            self.pipette_type = 'single'
        return

    def update(self, _line, _line_type):
        if _line_type is 'aspirate':
            self._update_source(_line)
        elif _line_type is 'dispense':
            self._update_dest(_line)
        self.last_action_type = _line_type
        return

    def _update_source(self, _line):
        # I could combine the regexs in one but why bother
        amount = re.findall(AMOUNT_ASPIRATED, _line)
        assert amount is not None, 'amount lookup failed in "{}"'.format(_line)
        amount = amount[0]
        source_well = re.findall(SOURCE_WELL, _line)
        assert source_well is not None, 'source_well lookup failed in "{}"'.format(_line)
        source_well = source_well[0]
        source_slot = re.findall(DECK_SLOT, _line)
        assert source_slot is not None, 'source_slot lookup failed in "{}"'.format(_line)
        source_slot = source_slot[0]
        # print(source_slot, source_well, amount)
        self.source.append(Source(slot=source_slot, well=source_well, amount=amount))
        return

    def _update_dest(self, _line):
        # I could combine the regexs in one but why bother
        amount = re.findall(AMOUNT_DISPENSED, _line)
        assert amount is not None, 'amount lookup failed in "{}"'.format(_line)
        amount = amount[0]
        dest_well = re.findall(DEST_WELL, _line)
        assert dest_well is not None, 'source_well lookup failed in "{}"'.format(_line)
        dest_well = dest_well[0]
        dest_slot = re.findall(DECK_SLOT, _line)
        assert dest_slot is not None, 'source_slot lookup failed in "{}"'.format(_line)
        dest_slot = dest_slot[0]
        # print(dest_slot, dest_well, amount)
        self.dest.append(Dest(slot=dest_slot, well=dest_well, amount=amount))
        return

    def get_last_action_type(self):
        return self.last_action_type

    def get_pipette_type(self):
        return self.pipette_type

    def close(self):
        self.is_closed = True

    def create_log(self):
        """
        Always all aspirate first and dispense at the end, otherwise it's a new actions_list.
        Do a check that the sum of aspirate is the same as the sum of dispense
        """
        _rows = 'ABCDEFGH'
        aspirate_sum = sum(float(x.amount) for x in self.source)
        dispense_sum = sum(float(x.amount) for x in self.dest)
        assert aspirate_sum==dispense_sum, 'Aspirated volume is not equal to Dispensed volume'
        # check that aspirate is only from one well
        assert len(list(set((x.slot, x.well) for x in self.source))) == 1, 'Aspirate from multiple wells is not supported'
        # consolidate the aspirate volume, ditch aspirate amount
        # basically broadcast the unique aspirating well to all the dospensing wells
        _out = []
        for dst in self.dest:
            _out.append( OutLine(source_slot=self.source[0].slot,
                                 source_well=self.source[0].well,
                                 dest_slot=dst.slot,
                                 dest_well=dst.well,
                                 amount=dst.amount) )

        # if multichannel, expand to all rows
        if self.pipette_type == 'multi':
            out = []
            for entry in _out:
                re_out = re.findall(r'\d+$', entry.source_well)
                if len(re_out) == 0:
                    raise ValueError('Regex failed: cannot find a number at the end of the well name??')
                _src_col = re_out[0]
                re_out = re.findall(r'\d+$', entry.dest_well)
                if len(re_out) == 0:
                    raise ValueError('Regex failed: cannot find a number at the end of the well name??')
                _dst_col = re_out[0]
                out.extend([OutLine(source_slot=entry.source_slot,
                                   source_well=_row+_src_col,
                                   dest_slot=entry.dest_slot,
                                   dest_well=_row+_dst_col,
                                   amount=entry.amount) for _row in _rows])

        else:
            out = _out

        self.log = out
        return

    def get_log(self):
        return self.log

    def print_log(self, _fid):
        for line in self.log:
            print(','.join(line), file=_fid)

# end of Class

def parse_protocol(fname, fidout):

    actions_list = []
    last_line_type = ''
    is_action_open = False

    with open(fname,'r') as fid:
        for line in fid:
            # do we care about this line?
            line_type = which_type_of_line(line.strip(), LINE_TYPES)
            # if we don't, continue
            if line_type is None:
                continue

            if line_type is 'pickup': # no action should be running
                current_action = LiquidTransfer(line, line_type)
                is_action_open = True
            elif line_type is 'droptip': # close and archive
                if is_action_open: # usually droptip at start of protocol!
                    current_action.close()
                    actions_list.append(current_action)
                    is_action_open = False
            elif line_type is 'aspirate' and \
                 current_action.get_last_action_type() is 'dispense':
                # close and archive action
                # and start a new one
                # but we need to read the pipette type from the last action!
                # there will always be an opened action at this point
                pipette_type = current_action.get_pipette_type()
                current_action.close()
                is_action_open = False
                actions_list.append(current_action)
                # new action, with old pipette
                current_action = LiquidTransfer(line,
                                                line_type,
                                                pipette_type=pipette_type)
                is_action_open = True
            else: # an action should be running already
                current_action.update(line, line_type)

    for i, action in enumerate(actions_list):
        # print(i)
        action.create_log()
        action.print_log(fidout)

#%% ---------------------------------------------------------------------------

def main():


    # input parser
    parser = argparse.ArgumentParser(description="Parsse the output of a robot's protocol, output well mapping in csv-friendly format")
    parser.add_argument('protocol',
                        type=str)
    parser.add_argument('-o', '--output',
                        type=argparse.FileType('w'),
                        default=sys.stdout)

    args = parser.parse_args()
    protocol_fname = args.protocol
    fidout = args.output

    # main function
    parse_protocol(protocol_fname, fidout)


if __name__ == '__main__':
    main()
