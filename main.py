import nibabel as nib

scan = nib.load("scans/patient001.nii.gz")
print(scan)