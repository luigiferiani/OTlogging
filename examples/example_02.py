"""
@author lferiani
@date Sep 11th, 2019

Only use multichannel

Tip rack for water in 6
Tip rack for drugs (to change) in 3
Trough for water in 9

Source 96WPs in 2, 5, 8, 11
Destination 96WPs in 1, 4, 7, 10

Times 4:
    - Dispense 5ul of water on a plate, using multichanel pipette
    - Then dispense 3 ul of compound from the source 96 WP to its destination 96 WP.
        (while shuffling columns)


"""

import numpy as np
from opentrons import labware, instruments, robot

####################### user intuitive parameters

# multichannel pipette parameters and tipracks
multi_pipette_type = 'p10-Multi'
multi_pipette_mount = 'left'

tiprackdrugs_slots = ['3']
tiprackdrugs_type = 'opentrons-tiprack-10ul'
tiprackdrugs_startfrom = '1'

tiprackH2O_slot = '6'
tiprackH2O_type = 'opentrons-tiprack-10ul'
# tiprackH2O_startfrom = '1'

# water trough
H2O_source_slot = '9'
H2O_source_type = 'trough-12row'
H2O_source_well = 'A1'
H2O_volume = 5

# drugs source
drugs_source_slots = ['2','5','8','11']
drugs_source_type = '96-well-plate-pcr-thermofisher'
frombottom_off = +0.3 # mm from bottom of src wells
drugs_volume = 3


# destination plates
agar_thickness = +2.5 # mm from the bottom of the well
destination_slots = ['1','4','7','10']
destination_type = '96-well-plate-sqfb-whatman'

n_columns = 12

# create mapping from sources to destination.
# it is a dict, with:
# {(source slot, dest slot):(cols in source, cols in dest)}
drugs_mapping = {}
seed = 20190911 # for reproducibility. Let's use the experimental date for the actual experiment, something else for debugging
np.random.seed(seed)
src_cols = np.arange(n_columns) # array of column numbers
for ss, ds in zip(drugs_source_slots, destination_slots):
    # create entry in dict
    dst_cols = src_cols.copy() # array of column numbers to be shuffled
    np.random.shuffle(dst_cols) # shuffle columns in destination. This acts in place!!
    drugs_mapping[(ss,ds)] = (src_cols,dst_cols)

# print out drugs_mapping:
# for key, value in drugs_mapping.items():
#     _src_slot, _dst_slot = key
#     _src_cols, _dst_cols = value
#     for _src_col, _dst_col in zip(_src_cols, _dst_cols):
#         print('slot {0} col {1} --> slot {2} col {3}'.format(_src_slot, _src_col, _dst_slot, _dst_col))



############################# define custom multiwell plates

if '48-well-plate-sarsted' not in labware.list():
    custom_plate = labware.create(
        '48-well-plate-sarsted',        # name of you labware
        grid=(8, 6),                    # specify amount of (columns, rows)
        spacing=(12.4, 12.4),           # distances (mm) between each (column, row)
        diameter=10,                    # diameter (mm) of each well on the plate
        depth=17.05,                    # depth (mm) of each well on the plate
        volume=500)                     # Sarsted had a "volume of work"

    print('Wells in 48WP Sarsted:')
    for well in custom_plate.wells():
        print(well)

if '96-well-plate-sqfb-whatman' not in labware.list():
    custom_plate = labware.create(
        '96-well-plate-sqfb-whatman',   # name of you labware
        grid=(12, 8),              # specify amount of (columns, rows)
        spacing=(8.99, 8.99),      # distances (mm) between each (column, row)
        diameter=7.57,             # diameter (mm) of each well on the plate (here width at bottom)
        depth=10.35,               # depth (mm) of each well on the plate
        volume=650)                # this is the actual volume as per specs, not a "volume of work"

    print('Wells in 96WP Whatman:')
    for well in custom_plate.wells():
        print(well)

if '96-well-plate-pcr-thermofisher' not in labware.list():
    custom_plate = labware.create(
        '96-well-plate-pcr-thermofisher',   # name of you labware
        grid=(12, 8),              # specify amount of (columns, rows)
        spacing=(9.00, 9.00),      # distances (mm) between each (column, row)
        diameter=5.50,             # diameter (mm) of each well on the plate (here width at top!!)
        depth=15.00,               # depth (mm) of each well on the plate
        volume=200)                # as per manufacturer's website

    print('Wells in 96WP PCR Thermo Fisher:')
    for well in custom_plate.wells():
        print(well)

############################ define labware
# i.e. translate user-friendly parameters into opentrons language

# pipette and tiprack

# multi channel
if multi_pipette_type == 'p10-Multi': # this is mostly a check as we don't own other multichannel pipettes (and to not have swapped single/multi)
    tiprackdrugs = [labware.load(tiprackdrugs_type, slot) \
                      for slot in tiprackdrugs_slots]
    pipette_multi = instruments.P10_Multi(
        mount=multi_pipette_mount,
        tip_racks=tiprackdrugs)
pipette_multi.start_at_tip(tiprackdrugs[0].well(tiprackdrugs_startfrom))
pipette_multi.plunger_positions['drop_tip'] = -6
# I only associated the "drugs" tiprack to the pipette as this is the one I want to handle authomatically
# I'll manually handle pipetting water

# container for water
water_src_container = labware.load(H2O_source_type, H2O_source_slot)
water_src_well = water_src_container.wells(H2O_source_well)
# tiprack for water
tiprackwater = labware.load(tiprackH2O_type, tiprackH2O_slot)

# translate the drugs mapping dict in robot language
wells_mapping = {}
for key, value in drugs_mapping.items():
    # unpack slots
    _src_slot, _dst_slot = key
    _src_cols, _dst_cols = value
    # load labware for src and dst
    src_plate = labware.load(drugs_source_type, _src_slot)
    dst_plate = labware.load(destination_type,  _dst_slot)
    # create list of wells with the right offset
    # NOT YET FOLLOWING THE ORDER WE WANT
    src_wells = [well.bottom(frombottom_off) for well in src_plate.rows('A')]
    dst_wells = [well.bottom(agar_thickness) for well in dst_plate.rows('A')]
    # these are normal lists though so should be reshufflable
    src_wells = [src_wells[wi] for wi in _src_cols]
    dst_wells = [dst_wells[wi] for wi in _dst_cols]
    # store in wells_mapping
    wells_mapping[(src_plate, dst_plate)] = (src_wells, dst_wells)

# print(wells_mapping)


################### actions
# safety command
pipette_multi.drop_tip()

# stupid function to measure how many tips got used
def count_used_tips():
    tc=0
    for c in robot.commands():
        if 'Picking up tip wells' in c: # order of checks here matters
            tc+=8
        elif 'Picking up tip well' in c: # note the lack of s in well
            tc+=1
    print('Tips used so far: {}'.format(tc))
    return


# count_used_tips() # should be 0

wtcc = 0 # water tips column counter
# first put water, then drugs in plates
for plates_tuple, wells_tuple in wells_mapping.items():
    # unpack
    src_plate, dst_plate = plates_tuple
    src_wells, dst_wells = wells_tuple


    # manual water transfer
    # pipette_multi.pick_up_tip(tiprackwater.wells('A'+str(wtcc+1)))
    pipette_multi.pick_up_tip(tiprackwater.cols(str(wtcc+1)))
    pipette_multi.transfer(H2O_volume,
                           water_src_well,
                           dst_wells,
                           new_tip='never',
                           blow_out=True)
    pipette_multi.drop_tip()
    wtcc += 1

    # drug transfer
    pipette_multi.transfer(drugs_volume,
                            src_wells,
                            dst_wells,
                            new_tip='always',
                            blow_out=True)

    # for s,d in zip(src_wells, dst_wells):
    #     print('{} {} -> {} {}'.format(src_plate.parent, s[0], dst_plate.parent, d[0]))


    # count_used_tips()
    robot.pause(60)
    pipette_multi.reset_tip_tracking()
    # each time we add water and fill up a 96wp => expecting 104 tips every plate
    # so 104, 208, 312, 416
