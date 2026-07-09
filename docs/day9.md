Day 9 - Image Normalization, Histogram Analysis, Noise Reduction, and Basic Segmentation
Objective

Prepare CT images for future AI models by implementing essential medical image preprocessing techniques including normalization, histogram analysis, Gaussian filtering, and threshold-based segmentation.

Completed Tasks
Implemented Min-Max normalization to scale CT voxel intensities between 0 and 1.
Verified the normalization process by checking the minimum and maximum intensity values.
Learned why normalization is essential before training AI and deep learning models.
Visualized the intensity distribution of the CT scan using a histogram.
Interpreted histogram peaks corresponding to different tissue types such as air, soft tissue, and bone.
Implemented Gaussian filtering using SciPy to reduce image noise while preserving anatomical structures.
Compared the original CT slice with the Gaussian-filtered image to observe the effect of smoothing.
Implemented threshold-based segmentation to convert the CT image into a binary image.
Learned how different threshold values isolate different anatomical structures.
Built a three-panel comparison viewer displaying the Original, Gaussian Filtered, and Thresholded CT images side by side.
What I Learned
Medical AI models perform better when image intensities are normalized to a common range.
Histograms provide valuable insight into the distribution of voxel intensities and tissue characteristics within a CT scan.
Gaussian filtering reduces random image noise by averaging neighboring pixel values while maintaining important anatomical boundaries.
Thresholding is one of the simplest image segmentation techniques, where pixels above a selected intensity value are classified as foreground and the remaining pixels become background.
Lower threshold values retain more anatomical structures, while higher threshold values isolate only the brightest tissues such as bone and contrast-enhanced vessels.
A preprocessing pipeline is an essential step before applying advanced AI segmentation models such as U-Net or nnU-Net.
Current Status

The project now contains a complete medical image preprocessing pipeline capable of loading CT scans, normalizing voxel intensities, analyzing intensity distributions, reducing image noise, performing basic threshold-based segmentation, and visually comparing each preprocessing stage.