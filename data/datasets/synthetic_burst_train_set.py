import torch
import numpy as np
from PIL import Image
from data.data_processing.synthetic_burst_generation import rgb2rawburst, random_crop #syn_burst_utils
import torchvision.transforms as tfm
import cv2


class SyntheticBurst(torch.utils.data.Dataset):
    """ Synthetic burst dataset for joint denoising, demosaicking, and super-resolution. RAW Burst sequences are
    synthetically generated on the fly as follows. First, a single image is loaded from the base_dataset. The sampled
    image is converted to linear sensor space using the inverse camera pipeline employed in [1]. A burst
    sequence is then generated by adding random translations and rotations to the converted image. The generated burst
    is then converted is then mosaicked, and corrupted by random noise to obtain the RAW burst.

    [1] Unprocessing Images for Learned Raw Denoising, Brooks, Tim and Mildenhall, Ben and Xue, Tianfan and Chen,
    Jiawen and Sharlet, Dillon and Barron, Jonathan T, CVPR 2019
    """
    def __init__(self, base_dataset, burst_size=8, crop_sz=384, transform=tfm.ToTensor()):
        self.base_dataset = base_dataset

        self.burst_size = burst_size
        self.crop_sz = crop_sz
        self.transform = transform

        self.downsample_factor = 4
        self.burst_transformation_params = {'max_translation': 24.0,
                                            'max_rotation': 1.0,
                                            'max_shear': 0.0,
                                            'max_scale': 0.0,
                                            'border_crop': 24}

        self.image_processing_params = {'random_ccm': True, 'random_gains': True, 'smoothstep': True,
                                        'gamma': True,
                                        'add_noise': True}
        self.interpolation_type = 'bilinear'

    def __len__(self):
        return len(self.base_dataset)

    def __getitem__(self, index):
        """ Generates a synthetic burst
        args:
            index: Index of the image in the base_dataset used to generate the burst

        returns:
            burst: Generated LR RAW burst, a torch tensor of shape
                   [burst_size, 4, self.crop_sz / (2*self.downsample_factor), self.crop_sz / (2*self.downsample_factor)]
                   The 4 channels correspond to 'R', 'G', 'G', and 'B' values in the RGGB bayer mosaick.
                   The extra factor 2 in the denominator (2*self.downsample_factor) corresponds to the mosaicking
                   operation.

            frame_gt: The HR RGB ground truth in the linear sensor space, a torch tensor of shape
                      [3, self.crop_sz, self.crop_sz]

            flow_vectors: The ground truth flow vectors between a burst image and the base image (i.e. the first image in the burst).
                          The flow_vectors can be used to warp the burst images to the base frame, using the 'warp'
                          function in utils.warp package.
                          flow_vectors is torch tensor of shape
                          [burst_size, 2, self.crop_sz / self.downsample_factor, self.crop_sz / self.downsample_factor].
                          Note that the flow_vectors are in the LR RGB space, before mosaicking. Hence it has twice
                          the number of rows and columns, compared to the output burst.

                          NOTE: The flow_vectors are only available during training for the purpose of using any
                                auxiliary losses if needed. The flow_vectors will NOT be provided for the bursts in the
                                test set

            meta_info: A dictionary containing the parameters used to generate the synthetic burst.
        """
        frame = self.base_dataset[index]

        # Augmentation, e.g. convert to tensor
        if self.transform is not None:
            # frame = Image.fromarray(frame)
            frame = self.transform(frame)

        # Extract a random crop from the image
        crop_sz = self.crop_sz + 2 * self.burst_transformation_params.get('border_crop', 0)
        frame_crop = random_crop(frame, crop_sz)

        # Generate RAW burst
        burst, frame_gt, burst_rgb, flow_vectors, meta_info = rgb2rawburst(frame_crop,
                                                                           self.burst_size,
                                                                           self.downsample_factor,
                                                                           burst_transformation_params=self.burst_transformation_params,
                                                                           image_processing_params=self.image_processing_params,
                                                                           interpolation_type=self.interpolation_type
                                                                           )

        if self.burst_transformation_params.get('border_crop') is not None:
            border_crop = self.burst_transformation_params.get('border_crop')
            frame_gt = frame_gt[:, border_crop:-border_crop, border_crop:-border_crop]

        return burst, frame_gt, burst_rgb, flow_vectors, meta_info


class SyntheticBurstRGB(torch.utils.data.Dataset):
    """ Synthetic burst dataset for joint denoising, demosaicking, and super-resolution. RAW Burst sequences are
    synthetically generated on the fly as follows. First, a single image is loaded from the base_dataset. The sampled
    image is converted to linear sensor space using the inverse camera pipeline employed in [1]. A burst
    sequence is then generated by adding random translations and rotations to the converted image. The generated burst
    is then converted is then mosaicked, and corrupted by random noise to obtain the RAW burst.

    [1] Unprocessing Images for Learned Raw Denoising, Brooks, Tim and Mildenhall, Ben and Xue, Tianfan and Chen,
    Jiawen and Sharlet, Dillon and Barron, Jonathan T, CVPR 2019
    """
    def __init__(self, base_dataset, burst_size=8, crop_sz=384, transform=tfm.ToTensor()):
        self.base_dataset = base_dataset

        self.burst_size = burst_size
        self.crop_sz = crop_sz
        self.transform = transform

        self.downsample_factor = 4
        self.burst_transformation_params = {'max_translation': 24.0,
                                            'max_rotation': 1.0,
                                            'max_shear': 0.0,
                                            'max_scale': 0.0,
                                            'border_crop': 24}

        self.image_processing_params = {'random_ccm': False, 'random_gains': False, 'smoothstep': False,
                                        'gamma': False,
                                        'add_noise': False}
        self.interpolation_type = 'bilinear'

    def __len__(self):
        return len(self.base_dataset)

    def __getitem__(self, index):
        """ Generates a synthetic burst
        args:
            index: Index of the image in the base_dataset used to generate the burst

        returns:
            burst: Generated LR RAW burst, a torch tensor of shape
                   [burst_size, 4, self.crop_sz / (2*self.downsample_factor), self.crop_sz / (2*self.downsample_factor)]
                   The 4 channels correspond to 'R', 'G', 'G', and 'B' values in the RGGB bayer mosaick.
                   The extra factor 2 in the denominator (2*self.downsample_factor) corresponds to the mosaicking
                   operation.

            frame_gt: The HR RGB ground truth in the linear sensor space, a torch tensor of shape
                      [3, self.crop_sz, self.crop_sz]

            flow_vectors: The ground truth flow vectors between a burst image and the base image (i.e. the first image in the burst).
                          The flow_vectors can be used to warp the burst images to the base frame, using the 'warp'
                          function in utils.warp package.
                          flow_vectors is torch tensor of shape
                          [burst_size, 2, self.crop_sz / self.downsample_factor, self.crop_sz / self.downsample_factor].
                          Note that the flow_vectors are in the LR RGB space, before mosaicking. Hence it has twice
                          the number of rows and columns, compared to the output burst.

                          NOTE: The flow_vectors are only available during training for the purpose of using any
                                auxiliary losses if needed. The flow_vectors will NOT be provided for the bursts in the
                                test set

            meta_info: A dictionary containing the parameters used to generate the synthetic burst.
        """
        frame = self.base_dataset[index]

        # Augmentation, e.g. convert to tensor
        if self.transform is not None:
            # frame = Image.fromarray(frame)
            frame = self.transform(frame)

        # Extract a random crop from the image
        crop_sz = self.crop_sz + 2 * self.burst_transformation_params.get('border_crop', 0)
        frame_crop = random_crop(frame, crop_sz)

        # Generate RAW burst
        burst, frame_gt, burst_rgb, flow_vectors, meta_info = rgb2rawburst(frame_crop,
                                                                           self.burst_size,
                                                                           self.downsample_factor,
                                                                           burst_transformation_params=self.burst_transformation_params,
                                                                           image_processing_params=self.image_processing_params,
                                                                           interpolation_type=self.interpolation_type
                                                                           )

        if self.burst_transformation_params.get('border_crop') is not None:
            border_crop = self.burst_transformation_params.get('border_crop')
            frame_gt = frame_gt[:, border_crop:-border_crop, border_crop:-border_crop]

        return burst, frame_gt, burst_rgb, flow_vectors, meta_info


class SyntheticBurstRGBAligned(torch.utils.data.Dataset):
    """ Synthetic burst dataset for joint denoising, demosaicking, and super-resolution. RAW Burst sequences are
    synthetically generated on the fly as follows. First, a single image is loaded from the base_dataset. The sampled
    image is converted to linear sensor space using the inverse camera pipeline employed in [1]. A burst
    sequence is then generated by adding random translations and rotations to the converted image. The generated burst
    is then converted is then mosaicked, and corrupted by random noise to obtain the RAW burst.

    [1] Unprocessing Images for Learned Raw Denoising, Brooks, Tim and Mildenhall, Ben and Xue, Tianfan and Chen,
    Jiawen and Sharlet, Dillon and Barron, Jonathan T, CVPR 2019
    """
    def __init__(self, base_dataset, burst_size=8, crop_sz=384, transform=tfm.ToTensor()):
        self.base_dataset = base_dataset

        self.burst_size = burst_size
        self.crop_sz = crop_sz
        self.transform = transform

        self.downsample_factor = 4
        self.burst_transformation_params = {'max_translation': 24.0,
                                            'max_rotation': 1.0,
                                            'max_shear': 0.0,
                                            'max_scale': 0.0,
                                            'border_crop': 24}

        self.image_processing_params = {'random_ccm': False, 'random_gains': False, 'smoothstep': False,
                                        'gamma': False,
                                        'add_noise': False}
        self.interpolation_type = 'bilinear'

    def __len__(self):
        return len(self.base_dataset)

    def __getitem__(self, index):
        """ Generates a synthetic burst
        args:
            index: Index of the image in the base_dataset used to generate the burst

        returns:
            burst: Generated LR RAW burst, a torch tensor of shape
                   [burst_size, 4, self.crop_sz / (2*self.downsample_factor), self.crop_sz / (2*self.downsample_factor)]
                   The 4 channels correspond to 'R', 'G', 'G', and 'B' values in the RGGB bayer mosaick.
                   The extra factor 2 in the denominator (2*self.downsample_factor) corresponds to the mosaicking
                   operation.

            frame_gt: The HR RGB ground truth in the linear sensor space, a torch tensor of shape
                      [3, self.crop_sz, self.crop_sz]

            flow_vectors: The ground truth flow vectors between a burst image and the base image (i.e. the first image in the burst).
                          The flow_vectors can be used to warp the burst images to the base frame, using the 'warp'
                          function in utils.warp package.
                          flow_vectors is torch tensor of shape
                          [burst_size, 2, self.crop_sz / self.downsample_factor, self.crop_sz / self.downsample_factor].
                          Note that the flow_vectors are in the LR RGB space, before mosaicking. Hence it has twice
                          the number of rows and columns, compared to the output burst.

                          NOTE: The flow_vectors are only available during training for the purpose of using any
                                auxiliary losses if needed. The flow_vectors will NOT be provided for the bursts in the
                                test set

            meta_info: A dictionary containing the parameters used to generate the synthetic burst.
        """
        frame = self.base_dataset[index]

        # Augmentation, e.g. convert to tensor
        if self.transform is not None:
            # frame = Image.fromarray(frame)
            frame = self.transform(frame)

        # Extract a random crop from the image
        crop_sz = self.crop_sz + 2 * self.burst_transformation_params.get('border_crop', 0)
        frame_crop = random_crop(frame, crop_sz)

        # Generate RAW burst
        burst, frame_gt, burst_rgb, flow_vectors, meta_info = rgb2rawburst(frame_crop,
                                                                           self.burst_size,
                                                                           self.downsample_factor,
                                                                           burst_transformation_params=self.burst_transformation_params,
                                                                           image_processing_params=self.image_processing_params,
                                                                           interpolation_type=self.interpolation_type
                                                                           )
        
        burst_rgb = self.align(burst_rgb)

        if self.burst_transformation_params.get('border_crop') is not None:
            border_crop = self.burst_transformation_params.get('border_crop')
            frame_gt = frame_gt[:, border_crop:-border_crop, border_crop:-border_crop]
        
        data = {}
        data['LR'] = burst_rgb
        data['HR'] = frame_gt

        return data
    
    def align(self, burst_rgb):
        # tensor to PIL numpy
        burst_rgb = burst_rgb.numpy()*255
        burst_rgb = burst_rgb.astype('uint8')
        burst_rgb = np.transpose(burst_rgb, (0, 2, 3, 1))
        # HOMOGRAPHY
        for i in range(1, 14):
            im1 = burst_rgb[0]
            im2 = burst_rgb[i]
            im1_gray = cv2.cvtColor(im1, cv2.COLOR_BGR2GRAY)
            im2_gray = cv2.cvtColor(im2, cv2.COLOR_BGR2GRAY)
            sz = im1.shape
            warp_mode = cv2.MOTION_HOMOGRAPHY
            if warp_mode == cv2.MOTION_HOMOGRAPHY:
                warp_matrix = np.eye(3, 3, dtype=np.float32)
            else:
                warp_matrix = np.eye(2, 3, dtype=np.float32)
            number_of_iterations = 10
            termination_eps = 1e-10
            criteria = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, number_of_iterations, termination_eps)
            try:
                # Run the ECC algorithm. The results are stored in warp_matrix.
                (cc, warp_matrix) = cv2.findTransformECC(im1_gray, im2_gray, warp_matrix, warp_mode, criteria)

                if warp_mode == cv2.MOTION_HOMOGRAPHY:
                    # Use warpPerspective for Homography
                    im2_aligned = cv2.warpPerspective(im2, warp_matrix, (sz[1], sz[0]),
                                                    flags=cv2.INTER_LINEAR + cv2.WARP_INVERSE_MAP)
                else:
                    # Use warpAffine for Translation, Euclidean and Affine
                    im2_aligned = cv2.warpAffine(im2, warp_matrix, (sz[1], sz[0]),
                                                flags=cv2.INTER_LINEAR + cv2.WARP_INVERSE_MAP)
                burst_rgb[i] = im2_aligned
            except:
                burst_rgb[i] = im1
        # PIL numpy to tensor
        burst_rgb = np.transpose(burst_rgb, (0, 3, 1, 2))
        burst_rgb = torch.from_numpy(burst_rgb) / 255.0
        burst_rgb = burst_rgb.clamp(0.0, 1.0)
        return burst_rgb