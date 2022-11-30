"""This is a very quick script to clean up the photo names
that current have some additional text after them in some cases"""

import os
photo_dir = "/home/humebc/projects/GlobalSearch/20210811_input_template_excels_CBASS84/cbass_84_photos"

for photo_name in os.listdir(photo_dir):
    if "IMG" in photo_name or "DSC" in photo_name:
        photobase = photo_name.split(".")[0]
        photobase = "_".join(photobase.split("_")[:-2])
        new_photo_name = photobase + ".jpg"

        os.rename(os.path.join(photo_dir, photo_name), os.path.join(photo_dir, new_photo_name))

# We also want to append the time to the dates
for photo_name in os.listdir(photo_dir):
    if "T1200" not in photo_name:
        new_photo_name = "_".join([photo_name.split("_")[0] + "T1200", "_".join(photo_name.split("_")[1:])])
        os.rename(os.path.join(photo_dir, photo_name), os.path.join(photo_dir, new_photo_name))

# we want to replace the CB with CBASS
for photo_name in os.listdir(photo_dir):
    if "CBASS" not in photo_name:
        new_photo_name = photo_name.replace("_CB_", "_CBASS_")
        os.rename(os.path.join(photo_dir, photo_name), os.path.join(photo_dir, new_photo_name))

# we want to replace the 01 with 1 etc.
for photo_name in os.listdir(photo_dir):
    if "_0" in photo_name:
        new_photo_name = photo_name.replace("_0", "_")
        os.rename(os.path.join(photo_dir, photo_name), os.path.join(photo_dir, new_photo_name))

