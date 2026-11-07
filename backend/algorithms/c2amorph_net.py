"""C2AMorph 네트워크 정의.

출처: 사용자 제공 Registration/HMCN/model/LFCAMorph.py (LapIRN 기반 3단계 diffeomorphic 정합).
LapIRN: Mok & Chung, "Large Deformation Diffeomorphic Image Registration with Laplacian Pyramid Networks", MICCAI 2020.
원본 대비 변경: (1) .cuda() 고정 호출을 DEVICE로 교체, (2) 누락된 Functions.py의 grid 함수를 LapIRN 공식 코드로 포함,
(3) dropblock 미설치 시 대체 클래스, (4) 실험용 __main__ 블록 제거. 네트워크 구조와 계산식은 바꾸지 않았다.
"""

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

try:
    from dropblock import DropBlock3D  # ResDrop 계열에서만 사용. C2AMorph(MRD_diff)는 쓰지 않는다.
except ImportError:  # pragma: no cover
    class DropBlock3D(nn.Module):
        def __init__(self, block_size=7, drop_prob=0.0):
            super().__init__()

        def forward(self, x):
            return x

DEVICE = torch.device('cpu')


def set_device(device):
    """모델 생성 전에 호출한다. 원본은 __init__에서 .to(DEVICE)를 고정 호출했다."""
    global DEVICE
    DEVICE = torch.device(device)


# 아래 두 함수는 LapIRN 공식 저장소 Code/Functions.py (commit c17fb75)와 같다.
def generate_grid(imgshape):
    x = np.arange(imgshape[0])
    y = np.arange(imgshape[1])
    z = np.arange(imgshape[2])
    grid = np.rollaxis(np.array(np.meshgrid(z, y, x)), 0, 4)
    grid = np.swapaxes(grid, 0, 2)
    grid = np.swapaxes(grid, 1, 2)
    return grid


def generate_grid_unit(imgshape):
    x = (np.arange(imgshape[0]) - ((imgshape[0] - 1) / 2)) / (imgshape[0] - 1) * 2
    y = (np.arange(imgshape[1]) - ((imgshape[1] - 1) / 2)) / (imgshape[1] - 1) * 2
    z = (np.arange(imgshape[2]) - ((imgshape[2] - 1) / 2)) / (imgshape[2] - 1) * 2
    grid = np.rollaxis(np.array(np.meshgrid(z, y, x)), 0, 4)
    grid = np.swapaxes(grid, 0, 2)
    grid = np.swapaxes(grid, 1, 2)
    return grid


class PreActBlock(nn.Module):
    '''Pre-activation version of the BasicBlock.'''
    expansion = 1

    def __init__(self, in_planes, planes, num_group=4, stride=1, bias=False):
        super(PreActBlock, self).__init__()
        self.conv1 = nn.Conv3d(in_planes, planes, kernel_size=3, stride=stride, padding=1, bias=bias)
        self.conv2 = nn.Conv3d(planes, planes, kernel_size=3, stride=1, padding=1, bias=bias)

        if stride != 1 or in_planes != self.expansion*planes:
            self.shortcut = nn.Sequential(
                nn.Conv3d(in_planes, self.expansion*planes, kernel_size=1, stride=stride, bias=bias)
            )


    def forward(self, x):
        out = F.leaky_relu(x, negative_slope=0.2)

        shortcut = self.shortcut(out) if hasattr(self, 'shortcut') else x
        out = self.conv1(out)

        out = self.conv2(F.leaky_relu(out, negative_slope=0.2))


        out += shortcut
        return out


class SpatialTransform_unit(nn.Module):
    def __init__(self):
        super(SpatialTransform_unit, self).__init__()

    def forward(self, x, flow, sample_grid):
        sample_grid = sample_grid + flow
        flow = torch.nn.functional.grid_sample(x, sample_grid, mode='bilinear', padding_mode="border", align_corners=True)
        return flow


class SpatialTransformNearest_unit(nn.Module):
    def __init__(self):
        super(SpatialTransformNearest_unit, self).__init__()

    def forward(self, x, flow, sample_grid):
        sample_grid = sample_grid + flow
        flow = torch.nn.functional.grid_sample(x, sample_grid, mode='nearest', padding_mode="border", align_corners=True)
        return flow


class DiffeomorphicTransform_unit(nn.Module):
    def __init__(self, time_step=7):
        super(DiffeomorphicTransform_unit, self).__init__()
        self.time_step = time_step

    def forward(self, velocity, sample_grid):
        flow = velocity/(2.0**self.time_step)
        # print(f'\tflow.shape : {flow.shape}')
        # print(f'\tsample_grid.shape : {sample_grid.shape}')
        for _ in range(self.time_step):
            # a = flow.permute(0, 2, 3, 4, 1)
            # print(f'\ta.shape : {a.shape}')
            grid = sample_grid + flow.permute(0,2,3,4,1)

            # print(f'\tgrid.shape : {grid.shape}')
            flow = flow + F.grid_sample(flow, grid, mode='bilinear', padding_mode="border", align_corners=True)
        return flow


class SpatialTransform(nn.Module):
    def __init__(self):
        super(SpatialTransform, self).__init__()

    def forward(self, x, flow, sample_grid):
        sample_grid = sample_grid + flow
        size_tensor = sample_grid.size()
        sample_grid[0, :, :, :, 0] = (sample_grid[0, :, :, :, 0] - ((size_tensor[3] - 1) / 2)) / (
                size_tensor[3] - 1) * 2
        sample_grid[0, :, :, :, 1] = (sample_grid[0, :, :, :, 1] - ((size_tensor[2] - 1) / 2)) / (
                size_tensor[2] - 1) * 2
        sample_grid[0, :, :, :, 2] = (sample_grid[0, :, :, :, 2] - ((size_tensor[1] - 1) / 2)) / (
                size_tensor[1] - 1) * 2
        flow = torch.nn.functional.grid_sample(x, sample_grid, mode='bilinear', align_corners=True)

        return flow


class SpatialTransformNearest(nn.Module):
    def __init__(self):
        super(SpatialTransformNearest, self).__init__()

    def forward(self, x, flow, sample_grid):
        sample_grid = sample_grid + flow
        size_tensor = sample_grid.size()
        sample_grid[0, :, :, :, 0] = (sample_grid[0, :, :, :, 0] - ((size_tensor[3] - 1) / 2)) / (
                    size_tensor[3] - 1) * 2
        sample_grid[0, :, :, :, 1] = (sample_grid[0, :, :, :, 1] - ((size_tensor[2] - 1) / 2)) / (
                    size_tensor[2] - 1) * 2
        sample_grid[0, :, :, :, 2] = (sample_grid[0, :, :, :, 2] - ((size_tensor[1] - 1) / 2)) / (
                    size_tensor[1] - 1) * 2
        flow = torch.nn.functional.grid_sample(x, sample_grid, mode='nearest', align_corners=True)

        return flow


class DiffeomorphicTransform(nn.Module):
    def __init__(self, time_step=7):
        super(DiffeomorphicTransform, self).__init__()
        self.time_step = time_step

    def forward(self, velocity, sample_grid, range_flow):
        flow = velocity / (2.0 ** self.time_step)
        size_tensor = sample_grid.size()
        # 0.5 flow
        for _ in range(self.time_step):
            grid = sample_grid + (flow.permute(0, 2, 3, 4, 1) * range_flow)
            grid[0, :, :, :, 0] = (grid[0, :, :, :, 0] - ((size_tensor[3] - 1) / 2)) / (size_tensor[3] - 1) * 2
            grid[0, :, :, :, 1] = (grid[0, :, :, :, 1] - ((size_tensor[2] - 1) / 2)) / (size_tensor[2] - 1) * 2
            grid[0, :, :, :, 2] = (grid[0, :, :, :, 2] - ((size_tensor[1] - 1) / 2)) / (size_tensor[1] - 1) * 2
            flow = flow + F.grid_sample(flow, grid, mode='bilinear', align_corners=True)
        return flow


def smoothloss(y_pred):
    dy = torch.abs(y_pred[:,:,1:, :, :] - y_pred[:,:, :-1, :, :])
    dx = torch.abs(y_pred[:,:,:, 1:, :] - y_pred[:,:, :, :-1, :])
    dz = torch.abs(y_pred[:,:,:, :, 1:] - y_pred[:,:, :, :, :-1])
    return (torch.mean(dx * dx)+torch.mean(dy*dy)+torch.mean(dz*dz))/3.0


def jacobian_det(deformation_field: torch.Tensor, lamb=None, normalize=True) -> torch.Tensor:
    # expects shape B,2,(D),H,W
    # returns shape B,1,(D),H,W")
    ndims = len(deformation_field.shape[2:])
    device = deformation_field.device

    if ndims == 2:
        if normalize:
            deformation_field = torch.stack((deformation_field[:, 0] * 2 / deformation_field.shape[-2],
                                             deformation_field[:, 1] * 2 / deformation_field.shape[-1]), 1)
        B, _, H, W = deformation_field.size()
        rep_x = nn.ReplicationPad2d((1, 1, 0, 0)).to(device)
        rep_y = nn.ReplicationPad2d((0, 0, 1, 1)).to(device)

        kernel_y = nn.Conv2d(2, 2, (3, 1), bias=False, groups=2).to(device)
        kernel_y.weight.data[:, 0, :, 0] = torch.tensor([-0.5, 0, 0.5]).view(1, 3).repeat(2, 1).to(device)
        kernel_x = nn.Conv2d(2, 2, (1, 3), bias=False, groups=2).to(device)
        kernel_x.weight.data[:, 0, 0, :] = torch.tensor([-0.5, 0, 0.5]).view(1, 3).repeat(2, 1).to(device)

        disp_field_vox = deformation_field.flip(1) * (torch.Tensor([H - 1, W - 1]).to(device).view(1, 2, 1, 1) - 1) / 2
        grad_y = kernel_y(rep_y(disp_field_vox))
        grad_x = kernel_x(rep_x(disp_field_vox))

        jacobian = torch.stack((grad_y, grad_x), 1) + torch.eye(2, 2).to(device).view(1, 2, 2, 1, 1)
        jac_det = jacobian[:, 0, 0, :, :] * jacobian[:, 1, 1, :, :] - jacobian[:, 1, 0, :, :] * jacobian[:, 0, 1, :, :]
    elif ndims == 3:
        if normalize:
            deformation_field = torch.stack((deformation_field[:, 0] * 2 / deformation_field.shape[-3],
                                             deformation_field[:, 1] * 2 / deformation_field.shape[-2],
                                             deformation_field[:, 2] * 2 / deformation_field.shape[-1]), 1)

        B, _, D, H, W = deformation_field.size()
        rep_x = nn.ReplicationPad3d((1, 1, 0, 0, 0, 0)).to(device)
        rep_y = nn.ReplicationPad3d((0, 0, 1, 1, 0, 0)).to(device)
        rep_z = nn.ReplicationPad3d((0, 0, 0, 0, 1, 1)).to(device)

        kernel_z = nn.Conv3d(3, 3, (3, 1, 1), bias=False, groups=3).to(device)
        kernel_z.weight.data[:, 0, :, 0, 0] = torch.tensor([-0.5, 0, 0.5]).view(1, 3).repeat(3, 1).to(device)
        kernel_y = nn.Conv3d(3, 3, (1, 3, 1), bias=False, groups=3).to(device)
        kernel_y.weight.data[:, 0, 0, :, 0] = torch.tensor([-0.5, 0, 0.5]).view(1, 3).repeat(3, 1).to(device)
        kernel_x = nn.Conv3d(3, 3, (1, 1, 3), bias=False, groups=3).to(device)
        kernel_x.weight.data[:, 0, 0, 0, :] = torch.tensor([-0.5, 0, 0.5]).view(1, 3).repeat(3, 1).to(device)

        disp_field_vox = deformation_field.flip(1) * (
                    torch.Tensor([D - 1, H - 1, W - 1]).to(device).view(1, 3, 1, 1, 1) - 1) / 2
        grad_z = kernel_z(rep_z(disp_field_vox))
        grad_y = kernel_y(rep_y(disp_field_vox))
        grad_x = kernel_x(rep_x(disp_field_vox))

        jacobian = torch.stack((grad_z, grad_y, grad_x), 1)
        eye = torch.eye(3, 3).to(device).view(1, 3, 3, 1, 1, 1)
        jacobian = jacobian + eye
        jac_det = (jacobian[:, 0, 0, :, :, :] *
                   (jacobian[:, 1, 1, :, :, :] * jacobian[:, 2, 2, :, :, :] - jacobian[:, 2, 1, :, :, :] * jacobian[:,1, 2, :, :,:])
                   - jacobian[:, 0,1, :,:,:] *
                   (jacobian[:, 1, 0, :, :, :] * jacobian[:, 2, 2, :, :, :] - jacobian[:, 2, 0, :, :,:] * jacobian[:, 1, 2, :, :,:])
                   + jacobian[:, 0, 2, :,:, :] *
                   (jacobian[:, 1, 0, :, :, :] * jacobian[:, 2, 1, :, :, :] - jacobian[:, 2, 0, :, :,:] * jacobian[:, 1, 1, :, :, :]))
    return jac_det


def JDetStd(deformation_field: torch.Tensor, lamb=0, normalize=True) -> torch.Tensor:
    """The standard deviation of the Jacobian determinant as a regularization loss."""
    return lamb * jacobian_det(deformation_field, normalize=normalize).std()



def JacobianDet(y_pred, sample_grid):
    J = y_pred + sample_grid
    dy = J[:, 1:, :-1, :-1, :] - J[:, :-1, :-1, :-1, :]
    dx = J[:, :-1, 1:, :-1, :] - J[:, :-1, :-1, :-1, :]
    dz = J[:, :-1, :-1, 1:, :] - J[:, :-1, :-1, :-1, :]

    Jdet0 = dx[:,:,:,:,0] * (dy[:,:,:,:,1] * dz[:,:,:,:,2] - dy[:,:,:,:,2] * dz[:,:,:,:,1])
    Jdet1 = dx[:,:,:,:,1] * (dy[:,:,:,:,0] * dz[:,:,:,:,2] - dy[:,:,:,:,2] * dz[:,:,:,:,0])
    Jdet2 = dx[:,:,:,:,2] * (dy[:,:,:,:,0] * dz[:,:,:,:,1] - dy[:,:,:,:,1] * dz[:,:,:,:,0])

    Jdet = Jdet0 - Jdet1 + Jdet2

    return Jdet


def neg_Jdet_loss(y_pred, sample_grid):
    neg_Jdet = -1.0 * JacobianDet(y_pred, sample_grid)
    selected_neg_Jdet = F.relu(neg_Jdet)

    return torch.mean(selected_neg_Jdet)


class NCC(torch.nn.Module):
    """
    local (over window) normalized cross correlation
    """
    def __init__(self, win=5, eps=1e-8):
        super(NCC, self).__init__()
        self.win = win
        self.eps = eps
        self.w_temp = win

    def forward(self, I, J):
        ndims = 3
        win_size = self.w_temp

        # set window size
        if self.win is None:
            self.win = [5] * ndims
        else:
            self.win = [self.w_temp] * ndims

        weight_win_size = self.w_temp
        weight = torch.ones((1, 1, weight_win_size, weight_win_size, weight_win_size), device=I.device, requires_grad=False)
        conv_fn = F.conv3d

        # compute CC squares
        I2 = I*I
        J2 = J*J
        IJ = I*J

        # compute filters
        # compute local sums via convolution
        I_sum = conv_fn(I, weight, padding=int(win_size/2))
        J_sum = conv_fn(J, weight, padding=int(win_size/2))
        I2_sum = conv_fn(I2, weight, padding=int(win_size/2))
        J2_sum = conv_fn(J2, weight, padding=int(win_size/2))
        IJ_sum = conv_fn(IJ, weight, padding=int(win_size/2))

        # compute cross correlation
        win_size = np.prod(self.win)
        u_I = I_sum/win_size
        u_J = J_sum/win_size

        cross = IJ_sum - u_J*I_sum - u_I*J_sum + u_I*u_J*win_size
        I_var = I2_sum - 2 * u_I * I_sum + u_I*u_I*win_size
        J_var = J2_sum - 2 * u_J * J_sum + u_J*u_J*win_size

        cc = cross * cross / (I_var * J_var + self.eps)

        # return negative cc.
        return -1.0 * torch.mean(cc)


class multi_resolution_NCC(torch.nn.Module):
    """
    local (over window) normalized cross correlation
    """
    def  __init__(self, win=None, eps=1e-5, scale=3):
        super(multi_resolution_NCC, self).__init__()
        self.num_scale = scale
        self.similarity_metric = []

        for i in range(scale):
            self.similarity_metric.append(NCC(win=win - (i*2)))

    def forward(self, I, J):
        total_NCC = []

        for i in range(self.num_scale):
            current_NCC = self.similarity_metric[i](I, J)
            total_NCC.append(current_NCC/(2**i))

            I = nn.functional.avg_pool3d(I, kernel_size=3, stride=2, padding=1, count_include_pad=False)
            J = nn.functional.avg_pool3d(J, kernel_size=3, stride=2, padding=1, count_include_pad=False)

        return sum(total_NCC)

class kl_loss(nn.Module):
    def __init__(self):
        super(kl_loss, self).__init__()

    def __call__(self, flow_mean, flow_log_sigma):
        kl_div = -0.5 * torch.sum(1 + flow_log_sigma - flow_mean.pow(2) - flow_log_sigma.exp(), dim=[1, 2, 3, 4])
        return (kl_div.mean() / (flow_mean.size(0) * flow_mean.size(1) * flow_mean.size(2) * flow_mean.size(3) * flow_mean.size(4)))

class lamda_mse_loss(nn.Module):
    def __init__(self):
        super(lamda_mse_loss, self).__init__()
        self.image_sigma=1

    def __call__(self, x, y):
        return 1.0 / (self.image_sigma ** 2) * torch.mean( (x - y) ** 2 )


class ProbabilisticModel(nn.Module):
    def __init__(self, is_training=True):
        super(ProbabilisticModel, self).__init__()

        self.mean = torch.nn.Conv3d(in_channels=3, out_channels=3, kernel_size=3, padding=1)
        self.log_sigma = torch.nn.Conv3d(in_channels=3, out_channels=3, kernel_size=3, padding=1)

        # Manual Initialization
        self.mean.weight.data.normal_(0, 1e-5)
        self.log_sigma.weight.data.normal_(0, 1e-10)
        self.log_sigma.bias.data.fill_(-10.)


        self.is_training=is_training

    def forward(self, final_layer):
        flow_mean = self.mean(final_layer)
        flow_log_sigma = self.log_sigma(final_layer)
        noise = torch.randn_like(flow_mean).to(DEVICE)

        if self.is_training:
            flow = flow_mean + flow_log_sigma * noise
        else:
            flow = flow_mean + flow_log_sigma # No noise at testing time

        return flow, flow_mean, flow_log_sigma

class contrastive_loss(nn.Module):
    def __init__(self, batch_size=8, temperature=0.5, use_cosine_similarity=True):
        super(contrastive_loss, self).__init__()
        self.batch_size = batch_size
        self.temperature = temperature
        self.softmax = torch.nn.Softmax(dim=-1)
        self.mask_samples_from_same_repr = self._get_correlated_mask().type(torch.bool)
        self.similarity_function = self._get_similarity_function(use_cosine_similarity)
        self.criterion = torch.nn.CrossEntropyLoss(reduction="sum")

    def _get_similarity_function(self, use_cosine_similarity):
        if use_cosine_similarity:
            self._cosine_similarity = torch.nn.CosineSimilarity(dim=-1)
            return self._cosine_simililarity
        else:
            return self._dot_simililarity

    def _get_correlated_mask(self):
        diag = np.eye(2 * self.batch_size)
        l1 = np.eye((2 * self.batch_size), 2 * self.batch_size, k=-self.batch_size)
        l2 = np.eye((2 * self.batch_size), 2 * self.batch_size, k=self.batch_size)
        mask = torch.from_numpy((diag + l1 + l2))
        mask = (1 - mask).type(torch.bool)
        return mask.to(DEVICE)

    @staticmethod
    def _dot_simililarity(x, y):
        v = torch.tensordot(x.unsqueeze(1), y.T.unsqueeze(0), dims=2)
        # x shape: (N, 1, C)
        # y shape: (1, C, 2N)
        # v shape: (N, 2N)
        return v

    def _cosine_simililarity(self, x, y):
        # x shape: (N, 1, C)
        # y shape: (1, 2N, C)
        # v shape: (N, 2N)
        v = self._cosine_similarity(x.unsqueeze(1), y.unsqueeze(0))
        return v

    def __call__(self, zis, zjs):
        # print(1, zjs.shape)
        representations = torch.cat([zjs, zis], dim=0)

        similarity_matrix = self.similarity_function(representations, representations)

        # filter out the scores from the positive samples
        l_pos = torch.diag(similarity_matrix, self.batch_size)
        r_pos = torch.diag(similarity_matrix, -self.batch_size)
        # print(f'l_pos.shape : {l_pos.shape} r_pos.shape : {r_pos.shape}')
        positives = torch.cat([l_pos, r_pos]).view(2 * self.batch_size, 1)
        negatives = similarity_matrix[self.mask_samples_from_same_repr].view(2 * self.batch_size, -1)

        logits = torch.cat((positives, negatives), dim=1)
        logits /= self.temperature
        # print('logits:', logits)

        labels = torch.zeros(2 * self.batch_size).to(DEVICE).long()
        loss = self.criterion(logits, labels)

        return loss / (2 * self.batch_size)



class Multi_Scale_Fire3(nn.Module):
    def __init__(self, in_ch, sq_ch, exp_ch):
        '''
        This is Multi_scale 4 parallel method
        :param in_ch: input_channel
        :param sq_ch: 1st 1x1 conv layer output_channel
        :param exp_ch: after 1x1 conv layer, each parallel layer output_channel

        '''
        super(Multi_Scale_Fire3, self).__init__()
        self.squeeze_layer = nn.Conv3d(in_ch, sq_ch, kernel_size=(1, 1, 1), stride=(1, 1, 1))
        self.expand_layer1_1x1 = nn.Conv3d(sq_ch, exp_ch, kernel_size=(1, 1, 1), stride=(1, 1, 1))
        self.expand_layer2_3x3 = nn.Conv3d(sq_ch, exp_ch, kernel_size=(3, 3, 3), stride=(1, 1, 1), padding=(1, 1, 1))
        self.expand_layer2_5x5 = nn.Conv3d(sq_ch, exp_ch, kernel_size=(3, 3, 3), dilation=(2,2,2), padding=(2, 2, 2))
        # self.expnad_layer2_7x7 = nn.Conv3d(sq_ch, exp_ch, kernel_size=(3, 3, 3), dilation=(3, 3, 3), padding=(3, 3, 3))

        # self.expnad_layer2_7x7 = nn.Conv3d(sq_ch, exp_ch, kernel_size=(3, 3, 3), dilation=(5,5,5), padding=(5,5,5))

        # self.expnad_layer3_1x1 = nn.Conv3d(exp_ch1, exp_ch3, kernel_size=(1, 1, 1), stride=(1, 1, 1))
        # self.expnad_layer4_3x3 = nn.Conv3d(exp_ch1, exp_ch3, kernel_size=(3, 3, 3), stride=(1, 1, 1),padding=(1, 1, 1))

        # self.expnad_layer5_1x1 = nn.Conv3d(exp_ch2, exp_ch3, kernel_size=(1, 1, 1), stride=(1, 1, 1))
        # self.expnad_layer6_3x3 = nn.Conv3d(exp_ch2, exp_ch3, kernel_size=(3, 3, 3), stride=(1, 1, 1),padding=(1, 1, 1))

        # self.relu = nn.ReLU(inplace=True)
        self.relu = nn.LeakyReLU(0.2)

    def forward(self, x):
        # print(" MSF3 x.shape : {}".format(x.shape))
        x1 = self.squeeze_layer(x)
        # print(" MSF3 x1.shape : {}".format(x1.shape))
        x1_1 = self.expand_layer1_1x1(x1)
        # print(" MSF3 x1_1.shape : {}".format(x1_1.shape))
        x1_3 = self.expand_layer2_3x3(x1)
        # print(" MSF3 x1_3.shape : {}".format(x1_3.shape))
        x1_5 = self.expand_layer2_5x5(x1)
        # print(" MSF3 x1_5.shape : {}".format(x1_5.shape))
        # x1_7 = self.expnad_layer2_7x7(x1)
        # print("x1_7.shape : {}".format(x1_7.shape))
        # xc3 = self.relu(torch.cat((x1_1, x1_3, x1_5, x1_7), dim=1))
        xc3 = self.relu(torch.cat((x1_1, x1_3, x1_5), dim=1))
        # print(" MSF3 xc3.shape : {}".format(xc3.shape))
        # print()
        return xc3

class Multi_Scale_Fire4(nn.Module):
    def __init__(self, in_ch, sq_ch, exp_ch):
        '''

        :param in_ch: input_channel
        :param sq_ch: 1st 1x1 conv layer output_channel
        :param exp_ch: after 1x1 conv layer, each parallel layer output_channel

        '''
        super(Multi_Scale_Fire4, self).__init__()
        self.squeeze_layer = nn.Conv3d(in_ch, sq_ch, kernel_size=(1, 1, 1), stride=(1, 1, 1))
        self.expand_layer1_1x1 = nn.Conv3d(sq_ch, exp_ch, kernel_size=(1, 1, 1), stride=(1, 1, 1))
        self.expand_layer2_3x3 = nn.Conv3d(sq_ch, exp_ch, kernel_size=(3, 3, 3), stride=(1, 1, 1), padding=(1, 1, 1))
        self.expand_layer2_5x5 = nn.Conv3d(sq_ch, exp_ch, kernel_size=(3, 3, 3), dilation=(2,2,2), padding=(2, 2, 2))
        self.expand_layer2_7x7 = nn.Conv3d(sq_ch, exp_ch, kernel_size=(3, 3, 3), dilation=(3, 3, 3), padding=(3, 3, 3))

        # self.expnad_layer2_7x7 = nn.Conv3d(sq_ch, exp_ch, kernel_size=(3, 3, 3), dilation=(5,5,5), padding=(5,5,5))

        # self.expnad_layer3_1x1 = nn.Conv3d(exp_ch1, exp_ch3, kernel_size=(1, 1, 1), stride=(1, 1, 1))
        # self.expnad_layer4_3x3 = nn.Conv3d(exp_ch1, exp_ch3, kernel_size=(3, 3, 3), stride=(1, 1, 1),padding=(1, 1, 1))

        # self.expnad_layer5_1x1 = nn.Conv3d(exp_ch2, exp_ch3, kernel_size=(1, 1, 1), stride=(1, 1, 1))
        # self.expnad_layer6_3x3 = nn.Conv3d(exp_ch2, exp_ch3, kernel_size=(3, 3, 3), stride=(1, 1, 1),padding=(1, 1, 1))

        # self.relu = nn.ReLU(inplace=True)
        self.relu = nn.LeakyReLU(0.2)

    def forward(self, x):
        # print(" MSF4 x.shape : {}".format(x.shape))
        x1 = self.squeeze_layer(x)
        # print(" MSF4 x1.shape : {}".format(x1.shape))
        x1_1 = self.expand_layer1_1x1(x1)
        # print(" MSF4 x1_1.shape : {}".format(x1_1.shape))
        x1_3 = self.expand_layer2_3x3(x1)
        # print(" MSF4 x1_3.shape : {}".format(x1_3.shape))
        x1_5 = self.expand_layer2_5x5(x1)
        # print(" MSF4 x1_5.shape : {}".format(x1_5.shape))
        x1_7 = self.expand_layer2_7x7(x1)
        # print(" MSF4 x1_7.shape : {}".format(x1_7.shape))
        xc3 = self.relu(torch.cat((x1_1, x1_3, x1_5, x1_7), dim=1))
        # print(" MSF4 xc3.shape : {}".format(xc3.shape))
        # print()
        return xc3

class MultiResblock(torch.nn.Module):
    '''
    MultiRes Block - only CNN 3x3

    Arguments:
        num_in_channels {int} -- Number of channels coming into mutlires block
        num_filters {int} -- Number of filters output
        # alpha {float} -- alpha hyperparameter (paper default: 1.67)

    '''

    def __init__(self, num_in_channels, num_filters, alpha=1):
        super().__init__()
        self.alpha = alpha
        self.W = num_filters * alpha


        if self.W <= 3:
            filt_cnt_3x3 = 1
            filt_cnt_7x7 = 1
            filt_cnt_5x5 = 1
        else:
            filt_cnt_3x3 = int(round(self.W * 0.167))
            filt_cnt_7x7 = int(round(self.W * 0.5))
            filt_cnt_5x5 = self.W - (filt_cnt_3x3 + filt_cnt_7x7)

        num_out_filters = filt_cnt_3x3 + filt_cnt_5x5 + filt_cnt_7x7

        self.shortcut = torch.nn.Conv3d(in_channels=num_in_channels, out_channels=num_out_filters, kernel_size=(1, 1, 1),padding=0)

        self.conv_3x3 =nn.Sequential(
            torch.nn.Conv3d(in_channels=num_in_channels, out_channels=filt_cnt_3x3, kernel_size=(3, 3, 3), padding=1),
            torch.nn.BatchNorm3d(filt_cnt_3x3)
        )

        self.conv_5x5 = nn.Sequential(
            torch.nn.Conv3d(in_channels=filt_cnt_3x3, out_channels=filt_cnt_5x5, kernel_size=(3, 3, 3), padding=1),
            torch.nn.BatchNorm3d(filt_cnt_5x5)
        )

        self.conv_7x7 = nn.Sequential(
            torch.nn.Conv3d(in_channels=filt_cnt_5x5, out_channels=filt_cnt_7x7, kernel_size=(3, 3, 3), padding=1),
            torch.nn.BatchNorm3d(filt_cnt_7x7)
        )

        self.batch_norm1 = torch.nn.BatchNorm3d(num_out_filters)
        self.batch_norm2 = torch.nn.BatchNorm3d(num_out_filters)
        self.relu = nn.LeakyReLU(0.2)

    def forward(self, x):
        # print(" MR x.shape : {}".format(x.shape))
        shrtct = self.shortcut(x)
        # print(" MR shrtct.shape : {}".format(shrtct.shape))
        a = self.conv_3x3(x)
        # print(" MR a.shape : {}".format(a.shape))
        b = self.conv_5x5(a)
        # print(" MR b.shape : {}".format(b.shape))
        c = self.conv_7x7(b)
        # print(" MR c.shape : {}".format(c.shape))

        x = torch.cat([a, b, c], axis=1)
        # print(" MR x.shape : {}".format(x.shape))
        x = self.batch_norm1(x)
        # print(" MR x.shape after batch_norm1: {}".format(x.shape))

        x = x + shrtct
        # print(" MR x.shape after + :  {}".format(x.shape))
        x = self.batch_norm2(x)
        # print(" MR x.shape after batch_norm2: {}".format(x.shape))
        # x = torch.nn.functional.relu(x)
        x = self.relu(x)
        # print(" MR x.shape after leakyReLu: {}".format(x.shape))
        # print()
        return x

class MultiResblock_dil(torch.nn.Module):
    '''
    MultiRes Block - YG - dilated Version

    Arguments:
        num_in_channels {int} -- Number of channels coming into mutlires block
        num_filters {int} -- Number of filters in a corrsponding UNet stage
        # alpha {float} -- alpha hyperparameter (default: 1.67)

    '''

    def __init__(self, num_in_channels, num_filters, alpha=1.67):
        super().__init__()
        self.alpha = alpha
        self.W = num_filters * alpha

        if self.W <= 3:
            filt_cnt_3x3 = 1
            filt_cnt_7x7 = 1
            filt_cnt_5x5 = 1
        else:
            filt_cnt_3x3 = int(round(self.W * 0.167))
            filt_cnt_7x7 = int(round(self.W * 0.5))
            filt_cnt_5x5 = self.W - (filt_cnt_3x3 + filt_cnt_7x7)

        num_out_filters = filt_cnt_3x3 + filt_cnt_5x5 + filt_cnt_7x7


        self.shortcut = torch.nn.Conv3d(in_channels=num_in_channels, out_channels=num_out_filters, kernel_size=(1, 1, 1),padding=0)

        self.conv_3x3 =nn.Sequential(
            torch.nn.Conv3d(in_channels=num_in_channels, out_channels=filt_cnt_3x3, kernel_size=(3, 3, 3), padding=1),
            torch.nn.BatchNorm3d(filt_cnt_3x3)
        )

        self.conv_5x5 = nn.Sequential(
            torch.nn.Conv3d(in_channels=filt_cnt_3x3, out_channels=filt_cnt_5x5, kernel_size=(3, 3, 3), dilation=2,padding=2),
            torch.nn.BatchNorm3d(filt_cnt_5x5)
        )

        self.conv_7x7 = nn.Sequential(
            torch.nn.Conv3d(in_channels=filt_cnt_5x5, out_channels=filt_cnt_7x7, kernel_size=(3, 3, 3), dilation=3, padding=3),
            torch.nn.BatchNorm3d(filt_cnt_7x7)
        )

        self.batch_norm1 = torch.nn.BatchNorm3d(num_out_filters)
        self.batch_norm2 = torch.nn.BatchNorm3d(num_out_filters)
        self.relu = nn.LeakyReLU(0.2)

    def forward(self, x):
        shrtct = self.shortcut(x)
        # print(" MRD shrtct.shape : {}".format(shrtct.shape))
        a = self.conv_3x3(x)
        # print(" MRD a.shape : {}".format(a.shape))
        b = self.conv_5x5(a)
        # print(" MRD b.shape : {}".format(b.shape))
        c = self.conv_7x7(b)
        # print(" MRD c.shape : {}".format(c.shape))

        x = torch.cat([a, b, c], axis=1)
        # print(" MRD x.shape : {}".format(x.shape))
        x = self.batch_norm1(x)
        # print(" MRD x.shape after batch_norm1: {}".format(x.shape))

        x = x + shrtct
        # print(" MRD x.shape after + :  {}".format(x.shape))
        x = self.batch_norm2(x)
        # print(" MRD x.shape after batch_norm2: {}".format(x.shape))
        # x = torch.nn.functional.relu(x)
        x = self.relu(x)
        # print(" MRD x.shape : {}".format(x.shape))
        # print()
        return x

class conv_pre_block(nn.Module):
    def __init__(self, ch_in, ch_out, batchnorm = True):
        '''
        Block for convolutional layer of U-Net at the encoder end.
        Args:
            ch_in : number of input channels
            ch_out : number of outut channels
        Returns:
            feature map of the given input
        '''
        super(conv_pre_block, self).__init__()
        if batchnorm :
            self.conv = nn.Sequential(
                nn.BatchNorm3d(ch_out),
                nn.ReLU(inplace=True),
                nn.Conv3d(ch_in, ch_out, kernel_size=(3, 3, 3), stride=(1, 1, 1), padding=(1, 1, 1), bias=True),
                nn.BatchNorm3d(ch_out),
                nn.ReLU(inplace=True),
                nn.Conv3d(ch_out, ch_out, kernel_size=(3, 3, 3), stride=(1, 1, 1), padding=(1, 1, 1), bias=True)
            )
        else:
            self.conv = nn.Sequential(
                nn.ReLU(inplace=True),
                nn.Conv3d(ch_in, ch_out, kernel_size=(3, 3, 3), stride=(1, 1, 1), padding=(1, 1, 1), bias=True),
                nn.ReLU(inplace=True),
                nn.Conv3d(ch_out, ch_out, kernel_size=(3, 3, 3), stride=(1, 1, 1), padding=(1, 1, 1), bias=True)
            )
    def forward(self, x):
        x = self.conv(x)
        return x

class conv_block(nn.Module):
    def __init__(self, ch_in, ch_out, batchnorm = True):
        '''
        Block for convolutional layer of U-Net at the encoder end.
        Args:
            ch_in : number of input channels
            ch_out : number of outut channels
        Returns:
            feature map of the given input
        '''
        super(conv_block, self).__init__()
        if batchnorm :
            self.conv = nn.Sequential(
                nn.Conv3d(ch_in, ch_out, kernel_size=(3, 3, 3), stride=(1, 1, 1), padding=(1, 1, 1), bias=True),
                nn.BatchNorm3d(ch_out),
                nn.ReLU(inplace=True),
                nn.Conv3d(ch_out, ch_out, kernel_size=(3, 3, 3), stride=(1, 1, 1), padding=(1, 1, 1), bias=True),
                nn.BatchNorm3d(ch_out),
                nn.ReLU(inplace=True)
            )
        else:
            self.conv = nn.Sequential(
                nn.Conv3d(ch_in, ch_out, kernel_size=(3, 3, 3), stride=(1, 1, 1), padding=(1, 1, 1), bias=True),
                nn.ReLU(inplace=True),
                nn.Conv3d(ch_out, ch_out, kernel_size=(3, 3, 3), stride=(1, 1, 1), padding=(1, 1, 1), bias=True),
                nn.ReLU(inplace=True)
            )
    def forward(self, x):
        x = self.conv(x)
        return x

class ResCNN_block(nn.Module):
    '''
    Residual convolution block
    Args:
    	ch_in  : number of input channels
    	ch_out : number of outut channels

    Returns:
    	feature map of the given input
    '''

    def __init__(self, ch_in, ch_out):
        super(ResCNN_block, self).__init__()
        self.Conv = conv_block(ch_in, ch_out)
        # self.Conv_1x1 = nn.Conv2d(ch_in, ch_out, kernel_size=1, stride=1, padding=0)
        self.Conv_1x1 = nn.Conv3d(ch_in, ch_out, kernel_size=(1, 1, 1), stride=(1, 1, 1), padding=0, bias=True)

    def forward(self, x):
        x1 = self.Conv_1x1(x)
        x = self.Conv(x)
        return x + x1

class ResCNN_pre_block(nn.Module):
    '''
    Residual convolution block
    Args:
    	ch_in  : number of input channels
    	ch_out : number of outut channels

    Returns:
    	feature map of the given input
    '''

    def __init__(self, ch_in, ch_out):
        super(ResCNN_pre_block, self).__init__()
        self.Conv = conv_pre_block(ch_out, ch_out)
        # self.Conv_1x1 = nn.Conv3d(ch_in, ch_out, kernel_size=(1, 1, 1), stride=(1, 1, 1), padding=0, bias=True)
        self.Conv_1x1 = nn.Conv3d(ch_in, ch_out, kernel_size=(1, 1, 1), stride=(1, 1, 1), padding=0, bias=True)

    def forward(self, x):

        x= self.Conv_1x1(x)
        # print(f'x.shape : {x.shape}')
        x1 = self.Conv(x)
        # print(f'x1.shape : {x1.shape}')
        return x + x1


class Recurrent_block(nn.Module):
    '''
    Recurrent convolution block for RU-Net and R2U-Net
    Args:
    	ch_out : number of outut channels
    	t: the number of recurrent convolution block to be used
    Returns:
    	feature map of the given input
    '''

    def __init__(self, ch_out, t=2):
        super(Recurrent_block, self).__init__()
        self.t = t
        self.ch_out = ch_out
        self.conv = nn.Sequential(
            # nn.Conv2d(ch_out, ch_out, kernel_size=3, stride=1, padding=1, bias=True),
            nn.Conv3d(ch_out, ch_out, kernel_size=(3, 3, 3), stride=(1, 1, 1), padding=(1, 1, 1), bias=True),
            nn.BatchNorm3d(ch_out),
            nn.ReLU(inplace=True)
        )

    def forward(self, x):
        # print(f'Recurrent_block x.shape : {x.shape}')
        for i in range(self.t):
            if i == 0:
                x1 = self.conv(x) #shared를 써서 그런거임

            x1 = self.conv(x + x1)
            # print(f'Recurrent_block x1.shape : {x1.shape}')
        return x1

class Recurrent_pre_block(nn.Module):
    '''
    Recurrent convolution block for RU-Net and R2U-Net
    Args:
    	ch_out : number of outut channels
    	t: the number of recurrent convolution block to be used
    Returns:
    	feature map of the given input
    '''

    def __init__(self, ch_out, t=2):
        super(Recurrent_pre_block, self).__init__()
        self.t = t
        self.ch_out = ch_out
        #conv가 하나만 되어있다는것은 하나로만 사용한다는것 - shared(이거 맞나?)
        self.conv_pre = nn.Sequential(
            nn.BatchNorm3d(ch_out),
            nn.ReLU(inplace=True),
            nn.Conv3d(ch_out, ch_out, kernel_size=(3, 3, 3), stride=(1, 1, 1), padding=(1, 1, 1), bias=True)
        )

    def forward(self, x):
        # print(f'Recurrent_pre_block x.shape : {x.shape}')
        for i in range(self.t):
            if i == 0:
                x1 = self.conv_pre(x)

            x1 = self.conv_pre(x + x1)
            # print(f'Recurrent_pre_block x1.shape : {x1.shape}')
        return x1

class ChannelPool(nn.Module):
    def forward(self, x):
        # print(f'\t\t ChannelPool x.shape : {x.shape}')
        # a = torch.max(x,1)
        # print(f'\t\t ChannelPool len(torch.max(x,1)) : {len(a)}')
        # b = torch.max(x, 1)[0]
        # print(f'\t\t ChannelPool torch.max(x, 1)[0].shape : {b.shape}')
        # c = torch.max(x,1)[0].unsqueeze(1)
        # print(f'\t\t ChannelPool torch.max(x,1)[0].unsqueeze(1).shape : {c.shape}')
        #
        # d = torch.mean(x,1).unsqueeze(1)
        # print(f'\t\t ChannelPool torch.mean(x,1).unsqueeze(1).shape : {d.shape}')
        return torch.cat( (torch.max(x,1)[0].unsqueeze(1), torch.mean(x,1).unsqueeze(1)), dim=1 )


class Spatial_attention(nn.Module):
    '''
    Residual spatial attention block
    '''

    def __init__(self,  kernel_size =7):
        super(Spatial_attention, self).__init__()

        self.compress = ChannelPool()
        self.conv_drop_block = Conv_drop_block(2, 1, activation=False)
        self.batch = nn.Sequential(
            nn.BatchNorm3d(1),
            nn.ReLU(inplace=True)
        )


    def forward(self, x_in):
        # print(f'\tspatial_attention x_in.shape : {x_in.shape}')
        x = self.compress(x_in)
        # print(f'\tspatial_attention x.shape : {x.shape}')
        x = self.conv_drop_block(x)
        # print(f'\tspatial_attention x.shape : {x.shape}')
        x = self.batch(x)
        # print(f'\tspatial_attention x.shape : {x.shape}')
        return x_in*x


class RSAB(nn.Module):
    '''
    Residual spatial attention block
    '''

    def __init__(self, ch_in, ch_mid):
        super(RSAB, self).__init__()
        self.conv_drop_block1 = Conv_drop_block(ch_in, ch_mid, activation=True)
        self.conv_drop_block2 = Conv_drop_block(ch_mid, ch_in, activation=False)
        self.batch1= nn.Sequential(
            nn.BatchNorm3d(ch_in),
            nn.ReLU(inplace=True)
        )
        self.batch2 = nn.Sequential(
            nn.BatchNorm3d(ch_in),
            nn.ReLU(inplace=True)
        )
        self.spatial_attn = Spatial_attention()
        self.conv = nn.Conv3d(ch_in, ch_mid, kernel_size=(3, 3, 3), stride=(1, 1, 1), padding=(1, 1, 1), bias=True)

    def forward(self, x_in):
        # print(f'res_spatial_attn_block x.shape : {x_in.shape}')
        x = self.batch1(x_in)
        # print(f'res_spatial_attn_block x1.shape : {x.shape}')
        x = self.conv_drop_block1(x)
        # print(f'res_spatial_attn_block x2.shape : {x.shape}')
        x = self.conv_drop_block2(x)
        # print(f'res_spatial_attn_block x3.shape : {x.shape}')
        x = self.spatial_attn(x)
        # print(f'res_spatial_attn_block x4.shape : {x.shape}')
        x = x_in + x
        # print(f'res_spatial_attn_block x5.shape : {x.shape}')
        x = self.batch2(x)
        # print(f'res_spatial_attn_block x6.shape : {x.shape}')
        return x



class RCNN_block(nn.Module):
    '''
    Recurrent convolution block for RU-Net
    Args:
    	ch_in  : number of input channels
    	ch_out : number of outut channels
    	t	: the number of recurrent residual convolution block to be used
    Returns:
    	feature map of the given input
    '''

    def __init__(self, ch_in, ch_out, t=2):
        super(RCNN_block, self).__init__()
        self.RCNN = nn.Sequential(
            Recurrent_block(ch_out, t=t),
            Recurrent_block(ch_out, t=t)
        )
        # self.Conv_1x1 = nn.Conv2d(ch_in, ch_out, kernel_size=1, stride=1, padding=0)
        self.Conv_1x1 = nn.Conv3d(ch_in, ch_out, kernel_size=(1, 1, 1), stride=(1, 1, 1), padding=0, bias=True)

    def forward(self, x):
        x = self.Conv_1x1(x)
        x = self.RCNN(x)
        return x

class RCNN_pre_block(nn.Module):
    '''
    Recurrent convolution block for RU-Net
    Args:
    	ch_in  : number of input channels
    	ch_out : number of outut channels
    	t	: the number of recurrent residual convolution block to be used
    Returns:
    	feature map of the given input
    '''

    def __init__(self, ch_in, ch_out, t=2):
        super(RCNN_pre_block, self).__init__()
        self.RCNN = nn.Sequential(
            Recurrent_pre_block(ch_out, t=t),
            Recurrent_pre_block(ch_out, t=t)
        )
        # self.Conv_1x1 = nn.Conv2d(ch_in, ch_out, kernel_size=1, stride=1, padding=0)
        self.Conv_1x1 = nn.Conv3d(ch_in, ch_out, kernel_size=(1, 1, 1), stride=(1, 1, 1), padding=0, bias=True)

    def forward(self, x):
        x = self.Conv_1x1(x)
        x = self.RCNN(x)
        return x


class RRCNN_block(nn.Module):
    '''
    Recurrent Residual convolution block for R2U-Net
    Args:
    	ch_in  : number of input channels
    	ch_out : number of outut channels
    	t	: the number of recurrent residual convolution block to be used
    Returns:
    	feature map of the given input
    '''

    def __init__(self, ch_in, ch_out, t=2):
        super(RRCNN_block, self).__init__()
        self.RCNN = nn.Sequential(
            Recurrent_block(ch_out, t=t),
            Recurrent_block(ch_out, t=t)
        )
        # self.Conv_1x1 = nn.Conv2d(ch_in, ch_out, kernel_size=1, stride=1, padding=0)
        self.Conv_1x1 = nn.Conv3d(ch_in, ch_out, kernel_size=(1,1,1), stride=(1, 1, 1), padding=0, bias=True)

    def forward(self, x):
        x = self.Conv_1x1(x)
        x1 = self.RCNN(x)
        return x + x1  # residual learning

class RRCNN_pre_block(nn.Module):
    '''
    Recurrent Residual convolution block for R2U-Net
    Args:
    	ch_in  : number of input channels
    	ch_out : number of outut channels
    	t	: the number of recurrent residual convolution block to be used
    Returns:
    	feature map of the given input
    '''

    def __init__(self, ch_in, ch_out, t=2):
        super(RRCNN_pre_block, self).__init__()
        self.RCNN = nn.Sequential(
            Recurrent_pre_block(ch_out, t=t),
            Recurrent_pre_block(ch_out, t=t)
        )
        # self.Conv_1x1 = nn.Conv2d(ch_in, ch_out, kernel_size=1, stride=1, padding=0)
        self.Conv_1x1 = nn.Conv3d(ch_in, ch_out, kernel_size=(1,1,1), stride=(1, 1, 1), padding=0, bias=True)

    def forward(self, x):
        x = self.Conv_1x1(x)
        x1 = self.RCNN(x)
        return x + x1  # residual learning

class Conv_drop_block(nn.Module):
    '''
    Recurrent convolution block for RU-Net and R2U-Net
    Args:
    	ch_out : number of outut channels
    	t: the number of recurrent convolution block to be used
    Returns:
    	feature map of the given input
    '''

    def __init__(self, ch_in, ch_out, activation=True, drop_block_size = 7, conv_drop_prob=0.9):
        super(Conv_drop_block, self).__init__()
        self.conv_drop_prob = conv_drop_prob
        self.drop_block_size = drop_block_size

        if activation :
            self.conv_drop = nn.Sequential(
                nn.Conv3d(ch_in, ch_out, kernel_size=(3, 3, 3), stride=(1, 1, 1), padding=(1, 1, 1), bias=True),
                DropBlock3D(block_size=self.drop_block_size, drop_prob=self.conv_drop_prob),
                nn.BatchNorm3d(ch_out),
                nn.ReLU()
            )
        else:
            self.conv_drop = nn.Sequential(
                nn.Conv3d(ch_in, ch_out, kernel_size=(3, 3, 3), stride=(1, 1, 1), padding=(1, 1, 1), bias=True),
                DropBlock3D(block_size=self.drop_block_size, drop_prob=self.conv_drop_prob)
            )

    def forward(self, x):
        # print(f"\tconv_drop_block x.shape : {x.shape}")
        x = self.conv_drop(x)
        # print(f"\tconv_drop_block x.shape : {x.shape}")
        return x

class Res_drop_block(nn.Module):
    '''
    Residual with dropblock
    '''

    def __init__(self, ch_in, ch_out):
        self.ch_in = ch_in
        self.ch_out = ch_out
        super(Res_drop_block, self).__init__()
        self.batch_in = nn.Sequential(
            nn.BatchNorm3d(ch_out),
            nn.ReLU(inplace=True)
        )
        self.conv1x1 = nn.Conv3d(ch_in, ch_out, kernel_size=(1, 1, 1), stride=(1, 1, 1))
        self.conv_drop_block1 = Conv_drop_block(ch_out, ch_out, activation=True)
        self.conv_drop_block2 = Conv_drop_block(ch_out, ch_out, activation=False)
        self.batch_out = nn.Sequential(
            nn.BatchNorm3d(ch_out),
            nn.ReLU(inplace=True)
        )


    def forward(self, x_in):
        if self.ch_in != self.ch_out:
            x_in = self.conv1x1(x_in)
        x = self.batch_in(x_in)
        # print(f'\t\t\tres_drop_block x.shape : {x.shape}')
        x = self.conv_drop_block1(x)
        # print(f'\t\t\tres_drop_block x.shape : {x.shape}')
        x = self.conv_drop_block2(x)
        # print(f'\t\t\tres_drop_block x.shape : {x.shape}')
        # print(f'\t\t\tres_drop_block x.shape : {x.shape}')
        # print(f'\t\t\tres_drop_block x_in.shape : {x_in.shape}')
        x = self.batch_out(x_in + x)
        return x

'''
def Attention1D(x, g, inter_channel):
    theta_x = Conv1D(inter_channel, [1], strides=[1])(x)
    phi_g = Conv1D(inter_channel, [1], strides=[1])(g)
    f = Activation('relu')(add([theta_x, phi_g]))
    psi_f = Conv1D(1, [1], strides=[1])(f)
    rate = Activation('sigmoid')(psi_f)
    att_x = multiply([x, rate])
    return att_x
'''

class Attention_block1D(nn.Module):
    def __init__(self, F_g, F_l, F_int):
        super(Attention_block, self).__init__()
        self.W_g = nn.Sequential(
            nn.Conv1d(F_g, F_int, kernel_size=1, stride=1, padding=0, bias=True),
            nn.BatchNorm1d(F_int)
        )

        self.W_x = nn.Sequential(
            nn.Conv1d(F_l, F_int, kernel_size=1, stride=1, padding=0, bias=True),
            nn.BatchNorm1d(F_int)
        )

        self.psi = nn.Sequential(
            nn.Conv1d(F_int, 1, kernel_size=1, stride=1, padding=0, bias=True),
            nn.BatchNorm1d(1),
            nn.Sigmoid()
        )

        self.relu = nn.ReLU(inplace=True)

    def forward(self, g, x):
        # print("   Attn1D x.shape : ", x.shape)
        # print("   Attn1D g.shape : ", g.shape)
        g1 = self.W_g(g)
        # print("   Attn1D g1.shape : ", g1.shape)
        x1 = self.W_x(x)
        # print("   Attn1D x1.shape : ", x1.shape)
        psi = self.relu(g1 + x1)
        # print("   Attn1D psi.shape : ", psi.shape)
        psi = self.psi(psi)
        # print("   Attn1D psi.shape : ", psi.shape)
        return x * psi

class Attention_block(nn.Module):
    def __init__(self, F_g, F_l, F_int, batch=True):
        super(Attention_block, self).__init__()
        if batch == True:
            self.W_g = nn.Sequential(
                nn.Conv3d(F_g, F_int, kernel_size=(1, 1, 1), stride=(1, 1, 1), padding=(0, 0, 0), bias=True),
                nn.BatchNorm3d(F_int)
            )

            self.W_x = nn.Sequential(
                nn.Conv3d(F_l, F_int, kernel_size=(1, 1, 1), stride=(1, 1, 1), padding=(0, 0, 0), bias=True),
                nn.BatchNorm3d(F_int)
            )

            self.psi = nn.Sequential(
                nn.Conv3d(F_int, 1, kernel_size=(1, 1, 1), stride=(1, 1, 1), padding=(0, 0, 0), bias=True),
                nn.BatchNorm3d(1),
                nn.Sigmoid()
            )
        else:
            self.W_g = nn.Sequential(
                nn.Conv3d(F_g, F_int, kernel_size=(1, 1, 1), stride=(1, 1, 1), padding=(0, 0, 0), bias=True)
            )

            self.W_x = nn.Sequential(
                nn.Conv3d(F_l, F_int, kernel_size=(1, 1, 1), stride=(1, 1, 1), padding=(0, 0, 0), bias=True)
            )

            self.psi = nn.Sequential(
                nn.Conv3d(F_int, 1, kernel_size=(1, 1, 1), stride=(1, 1, 1), padding=(0, 0, 0), bias=True),
                nn.Sigmoid()
            )
        self.relu = nn.ReLU(inplace=True)

    def forward(self, g, x):
        # print("   Attn x.shape : ", x.shape)
        # print("   Attn g.shape : ", g.shape)
        g1 = self.W_g(g)
        # print("   Attn g1.shape : ", g1.shape)
        x1 = self.W_x(x)
        # print("   Attn x1.shape : ", x1.shape)
        psi = self.relu(g1 + x1)
        # print("   Attn psi.shape : ", psi.shape)
        psi = self.psi(psi)
        # print("   Attn psi.shape : ", psi.shape)
        return x * psi

class Attn_w_Dil(nn.Module):
    def __init__(self, F_g, F_l, F_int, batch=True):
        super(Attn_w_Dil, self).__init__()
        if batch:
            self.W_g = nn.Sequential(
                nn.Conv3d(F_g, F_int, kernel_size=(1, 1, 1), stride=(1, 1, 1), padding=(0, 0, 0), bias=True),
                nn.Conv3d(F_int, F_int, kernel_size=(3, 3, 3), dilation=1, padding=1),
                nn.BatchNorm3d(F_int)
            )

            self.W_x = nn.Sequential(
                nn.Conv3d(F_l, F_int, kernel_size=(1, 1, 1), stride=(1, 1, 1), padding=(0, 0, 0), bias=True),
                nn.Conv3d(F_int, F_int, kernel_size=(3, 3, 3), dilation=1, padding=1),
                nn.BatchNorm3d(F_int)
            )

            self.psi = nn.Sequential(
                nn.Conv3d(F_int, 1, kernel_size=(1, 1, 1), stride=(1, 1, 1), padding=(0, 0, 0), bias=True),
                # nn.Conv3d(F_int, F_int, kernel_size=(3, 3, 3), dilation=1, padding=1),
                nn.BatchNorm3d(1),
                nn.Sigmoid()
            )
        else:
            self.W_g = nn.Sequential(
                nn.Conv3d(F_g, F_int, kernel_size=(1, 1, 1), stride=(1, 1, 1), padding=(0, 0, 0), bias=True),
                nn.Conv3d(F_int, F_int, kernel_size=(3, 3, 3), dilation=1, padding=1)
            )

            self.W_x = nn.Sequential(
                nn.Conv3d(F_l, F_int, kernel_size=(1, 1, 1), stride=(1, 1, 1), padding=(0, 0, 0), bias=True),
                nn.Conv3d(F_int, F_int, kernel_size=(3, 3, 3), dilation=1, padding=1),
            )

            self.psi = nn.Sequential(
                nn.Conv3d(F_int, 1, kernel_size=(1, 1, 1), stride=(1, 1, 1), padding=(0, 0, 0), bias=True),
                nn.Sigmoid()
            )

        self.relu = nn.ReLU(inplace=True)

    def forward(self, g, x):
        # print("   Attn x.shape : ", x.shape)
        # print("   Attn g.shape : ", g.shape)
        g1 = self.W_g(g)
        # print("   Attn g1.shape : ", g1.shape)
        x1 = self.W_x(x)
        # print("   Attn x1.shape : ", x1.shape)
        psi = self.relu(g1 + x1)
        # print("   Attn psi.shape : ", psi.shape)
        psi = self.psi(psi)
        # print("   Attn psi.shape : ", psi.shape)
        return x * psi

class MultiAttention(nn.Module):
    def __init__(self, F_g, F_l, F_int, batch= True, multiple=True, n_groups=4,):
        super(MultiAttention, self).__init__()
        self.multiple = multiple
        if batch :
            self.W_g_01 = nn.Sequential(
                nn.Conv3d(F_g, F_int, kernel_size=(1, 1, 1), padding=(0, 0, 0), bias=True),
                nn.Conv3d(F_int, F_int, kernel_size=(3, 3, 3), dilation=1, padding=1),
                nn.BatchNorm3d(F_int))
            # nn.GroupNorm(n_groups, F_int))
            self.W_x_01 = nn.Sequential(
                nn.Conv3d(F_l, F_int, kernel_size=(1, 1, 1), padding=(0, 0, 0), bias=True),
                nn.Conv3d(F_int, F_int, kernel_size=(3, 3, 3), dilation=2, padding=2),
                nn.BatchNorm3d(F_int))
            # nn.GroupNorm(n_groups, F_int))

            self.W_g_02 = nn.Sequential(
                nn.Conv3d(F_g, F_int, kernel_size=(1, 1, 1), padding=(0, 0, 0), bias=True),
                nn.Conv3d(F_int, F_int, kernel_size=(3, 3, 3), dilation=5, padding=5),
                nn.BatchNorm3d(F_int))
            # nn.GroupNorm(n_groups, F_int))
            self.W_x_02 = nn.Sequential(
                nn.Conv3d(F_l, F_int, kernel_size=(1, 1, 1), padding=(0, 0, 0), bias=True),
                nn.Conv3d(F_int, F_int, kernel_size=(3, 3, 3), dilation=7, padding=7),
                nn.BatchNorm3d(F_int))
            # nn.GroupNorm(n_groups, F_int))

            self.psi = nn.Sequential(
                nn.Conv3d(F_int, 1, kernel_size=(1, 1, 1), stride=(1, 1, 1), padding=(0, 0, 0), bias=True),
                # nn.GroupNorm(n_groups, 1),
                nn.BatchNorm3d(1),
                nn.Sigmoid())
        else:
            self.W_g_01 = nn.Sequential(
                nn.Conv3d(F_g, F_int, kernel_size=(1, 1, 1), padding=(0, 0, 0), bias=True),
                nn.Conv3d(F_int, F_int, kernel_size=(3, 3, 3), dilation=1, padding=1))
            self.W_x_01 = nn.Sequential(
                nn.Conv3d(F_l, F_int, kernel_size=(1, 1, 1), padding=(0, 0, 0), bias=True),
                nn.Conv3d(F_int, F_int, kernel_size=(3, 3, 3), dilation=2, padding=2))
            self.W_g_02 = nn.Sequential(
                nn.Conv3d(F_g, F_int, kernel_size=(1, 1, 1), padding=(0, 0, 0), bias=True),
                nn.Conv3d(F_int, F_int, kernel_size=(3, 3, 3), dilation=5, padding=5))
            self.W_x_02 = nn.Sequential(
                nn.Conv3d(F_l, F_int, kernel_size=(1, 1, 1), padding=(0, 0, 0), bias=True),
                nn.Conv3d(F_int, F_int, kernel_size=(3, 3, 3), dilation=7, padding=7))
            self.psi = nn.Sequential(
                nn.Conv3d(F_int, 1, kernel_size=(1, 1, 1), stride=(1, 1, 1), padding=(0, 0, 0), bias=True),
                nn.Sigmoid())
        self.relu = nn.ReLU(inplace=True)

    def forward(self, g, x):
        # print("   Attn Modi+ x.shape : ", x.shape)
        # print("   Attn Modi+ g.shape : ", g.shape)
        g1 = self.W_g_01(g)
        # print("   Attn Modi+ g1.shape : ", g1.shape)
        x1 = self.W_x_01(x)
        # print("   Attn Modi+ x1.shape : ", x1.shape)
        c1 = self.relu(g1 + x1)
        # print("   Attn Modi+ c1.shape : ", c1.shape)
        # print("   Attn Modi+ c1 shape", c1.shape)

        g2 = self.W_g_02(g)
        # print("   Attn Modi+ g2.shape : ", g2.shape)
        x2 = self.W_x_02(x)
        # print("   Attn Modi+ x2.shape : ", x2.shape)
        c2 = self.relu(g2 + x2)
        # print("   Attn Modi+ c2.shape : ", c2.shape)

        c_comb = self.relu(c1 + c2)
        psi_01 = self.psi(c_comb)
        # print("   Attn Modi+ psi_01.shape : ", psi_01.shape)
        # print()
        if self.multiple :
            return x * psi_01
        else:
            return x + psi_01


class model_diff_l1(nn.Module):
    def __init__(self, in_channel, ch_start, ch_start_magnitude, n_classes, is_train=True, imgshape=(160, 192, 144), range_flow=0.4,
                 model_name_front='unet_diff', model_name_back='both', doubleF=True, doubleB=True, batchsize=1,
                 attn='attn', attn_batch = True, attn_modi_multiple = True, concat='fea_e0'):
        super(model_diff_l1, self).__init__()

        self.in_channel = in_channel
        self.ch_start = ch_start
        self.ch_start_magnitude = ch_start_magnitude
        self.n_classes = n_classes


        self.model_name_front = model_name_front
        if model_name_back == 'both':
            self.model_name_back = model_name_front
            print("diff l1 self.model_name_back : ", self.model_name_back)
        else:
            self.model_name_back = model_name_back
            print("diff l1 self.model_name_back : ", self.model_name_back)
        self.doubleF = doubleF
        self.doubleB = doubleB

        self.attn = attn
        self.attn_batch = attn_batch
        # self.attn_mid_ch = attn_mid_ch
        self.attn_modi_multiple = attn_modi_multiple

        self.concat = concat
        if self.concat == 'e0':
            self.factor = 3
        elif self.concat == 'fea_e0':
            self.factor = 4



        self.batchsize = batchsize

        self.avgpool = torch.nn.AdaptiveAvgPool3d((1, 1, 1))
        self.linear_x = torch.nn.Linear(self.ch_start * ch_start_magnitude, self.ch_start * ch_start_magnitude)
        self.linear_y = torch.nn.Linear(self.ch_start * ch_start_magnitude, self.ch_start * ch_start_magnitude)


        self.range_flow = range_flow
        self.is_train = is_train

        self.imgshape = imgshape

        self.grid_1 = generate_grid_unit(self.imgshape)
        self.grid_1 = torch.from_numpy(np.reshape(self.grid_1, (1,) + self.grid_1.shape)).to(DEVICE).float()

        self.diff_transform = DiffeomorphicTransform_unit(time_step=7).to(DEVICE)
        self.transform = SpatialTransform_unit().to(DEVICE)


        bias_opt = False

        if self.model_name_front == 'unet_diff':
            self.input_encoder_lvl1 = self.input_feature_extract(self.in_channel//2, self.ch_start * ch_start_magnitude,
                                                                 doubleF=self.doubleF)

        elif self.model_name_front == 'MSF_diff':
            self.input_encoder_lvl1 = self.fire_front(self.in_channel//2, self.ch_start * ch_start_magnitude, doubleF=self.doubleF)

        elif self.model_name_front == 'MR_diff':
            self.input_encoder_lvl1 = self.multiresblock_front(self.in_channel//2, self.ch_start * ch_start_magnitude,
                                                               doubleF=self.doubleF)

        elif self.model_name_front == 'MRD_diff':
            self.input_encoder_lvl1 = self.multiresblock_dil_front(self.in_channel//2, self.ch_start * ch_start_magnitude,
                                                                   doubleF=self.doubleF)

        elif self.model_name_front == 'Res_diff':
            self.input_encoder_lvl1 = self.res_front(self.in_channel//2, self.ch_start * self.ch_start_magnitude,
                                                     doubleF=self.doubleF)

        elif self.model_name_front == 'Rec_diff':
            self.input_encoder_lvl1 = self.rec_front(self.in_channel//2, self.ch_start * self.ch_start_magnitude,
                                                     doubleF=self.doubleF)

        elif self.model_name_front == 'R2_diff':
            self.input_encoder_lvl1 = self.r2_front(self.in_channel//2, self.ch_start * self.ch_start_magnitude,
                                                    doubleF=self.doubleF)

        elif self.model_name_front == 'Res_pre_diff':
            self.input_encoder_lvl1 = self.res_pre_front(self.in_channel//2, self.ch_start * self.ch_start_magnitude,
                                                         doubleF=self.doubleF)

        elif self.model_name_front == 'Rec_pre_diff':
            self.input_encoder_lvl1 = self.rec_pre_front(self.in_channel//2, self.ch_start * self.ch_start_magnitude,
                                                         doubleF=self.doubleF)

        elif self.model_name_front == 'R2_pre_diff':
            self.input_encoder_lvl1 = self.r2_pre_front(self.in_channel//2, self.ch_start * self.ch_start_magnitude,
                                                        doubleF=self.doubleF)

        elif self.model_name_front == 'RSAB_diff':
            self.input_encoder_lvl1 = self.rsab_front(self.in_channel//2, self.ch_start * self.ch_start_magnitude,
                                                      doubleF=self.doubleF)
        elif self.model_name_front == 'ResDrop_diff':
            self.input_encoder_lvl1 = self.resdrop_front(self.in_channel//2, self.ch_start * self.ch_start_magnitude,
                                                         doubleF=self.doubleF)




        self.down_conv = nn.Conv3d(self.ch_start * self.ch_start_magnitude, self.ch_start * self.ch_start_magnitude, 3, stride=2, padding=1,
                                   bias=bias_opt)

        self.resblock_group_lvl1 = self.resblock_seq(self.ch_start * ch_start_magnitude*2, bias_opt=bias_opt)

        self.up = nn.ConvTranspose3d(self.ch_start * ch_start_magnitude*2 , self.ch_start * ch_start_magnitude, 2, stride=2,
                                     padding=0, output_padding=0, bias=bias_opt)

        if self.attn == 'attn':
            self.attention = Attention_block(self.ch_start * self.ch_start_magnitude, self.ch_start * self.ch_start_magnitude*2, self.ch_start * self.ch_start_magnitude*2, self.attn_batch)

        elif self.attn =='attn_w_Dil':
            self.attention = Attn_w_Dil(self.ch_start * self.ch_start_magnitude, self.ch_start * self.ch_start_magnitude*2, self.ch_start * self.ch_start_magnitude*2, self.attn_batch)

        elif self.attn == 'multi_attn':
            self.attention = MultiAttention(self.ch_start * self.ch_start_magnitude, self.ch_start * self.ch_start_magnitude*2,
                                                           self.ch_start * self.ch_start_magnitude*2, self.attn_batch, multiple=self.attn_modi_multiple)


        self.down_avg = nn.AvgPool3d(kernel_size=3, stride=2, padding=1, count_include_pad=False)

        if self.model_name_back == 'unet_diff':
            self.output_lvl1 = self.outputs(self.ch_start * ch_start_magnitude*self.factor, self.n_classes, kernel_size=3, stride=1, padding=1,
                                            bias=False, doubleB=self.doubleB)

        elif self.model_name_back == 'MSF_diff':
            self.output_lvl1 = self.fire_back(self.ch_start * ch_start_magnitude*self.factor, self.n_classes, doubleB=self.doubleB)

        elif self.model_name_back == 'MR_diff':
            self.output_lvl1 = self.multiresblock_back(self.ch_start * ch_start_magnitude*self.factor, self.n_classes, doubleB=self.doubleB)

        elif self.model_name_back == 'MRD_diff':
            self.output_lvl1 = self.multiresblock_dil_back(self.ch_start * ch_start_magnitude*self.factor, self.n_classes, doubleB=self.doubleB)

        elif self.model_name_back == 'Res_diff':
            self.output_lvl1 = self.res_back(self.ch_start * self.ch_start_magnitude*self.factor, self.n_classes, doubleB=self.doubleB)

        elif self.model_name_back == 'Rec_diff':
            self.output_lvl1 = self.rec_back(self.ch_start * self.ch_start_magnitude*self.factor, self.n_classes, doubleB=self.doubleB)

        elif self.model_name_back == 'R2_diff':
            self.output_lvl1 = self.r2_back(self.ch_start * self.ch_start_magnitude*self.factor, self.n_classes, doubleB=self.doubleB)

        elif self.model_name_back == 'Res_pre_diff':
            self.output_lvl1 = self.res_pre_back(self.ch_start * self.ch_start_magnitude*self.factor, self.n_classes, doubleB=self.doubleB)

        elif self.model_name_back == 'Rec_pre_diff':
            self.output_lvl1 = self.rec_pre_back(self.ch_start * self.ch_start_magnitude*self.factor, self.n_classes, doubleB=self.doubleB)

        elif self.model_name_back == 'R2_pre_diff':
            self.output_lvl1 = self.r2_pre_back(self.ch_start * self.ch_start_magnitude*self.factor, self.n_classes, doubleB=self.doubleB)

        elif self.model_name_back == 'RSAB_diff':
            self.output_lvl1 = self.rsab_back(self.ch_start * self.ch_start_magnitude*self.factor, self.n_classes, doubleB=self.doubleB)
        elif self.model_name_back == 'ResDrop_diff':
            self.output_lvl1 = self.resdrop_back(self.ch_start * self.ch_start_magnitude*self.factor, self.n_classes, doubleB=self.doubleB)


    def resblock_seq(self, in_channels, bias_opt=False):
        layer = nn.Sequential(
            PreActBlock(in_channels, in_channels, bias=bias_opt),
            nn.LeakyReLU(0.2),
            PreActBlock(in_channels, in_channels, bias=bias_opt),
            nn.LeakyReLU(0.2),
            PreActBlock(in_channels, in_channels, bias=bias_opt),
            nn.LeakyReLU(0.2),
            PreActBlock(in_channels, in_channels, bias=bias_opt),
            nn.LeakyReLU(0.2),
            PreActBlock(in_channels, in_channels, bias=bias_opt),
            nn.LeakyReLU(0.2)
        )
        return layer

    def input_feature_extract(self, in_channels, out_channels, kernel_size=3, stride=1, padding=1,
                              bias=False, doubleF=False):  # doubleF instead of batchnorm
        # print("input_feature_extract in_channels : {}, out_channels : {}".format(in_channels, out_channels))
        # print(f"doubleF : {doubleF}")
        if doubleF:
            layer = nn.Sequential(
                nn.Conv3d(in_channels, out_channels, kernel_size, stride=stride, padding=padding, bias=bias),
                nn.LeakyReLU(0.2),
                nn.Conv3d(out_channels, out_channels, kernel_size, stride=stride, padding=padding, bias=bias))
        else:
            layer = nn.Sequential(
                nn.Conv3d(in_channels, out_channels, kernel_size, stride=stride, padding=padding, bias=bias),
                nn.BatchNorm3d(out_channels),
                nn.ReLU())

        # print(f"layer : {layer}")
        return layer

    def fire_front(self, in_channels, out_channels, doubleF=False):
        # print("fire_front in_channels : {}, out_channels : {}".format(in_channels, out_channels))
        # print(f"doubleF : {doubleF}")
        if doubleF:
            layer = nn.Sequential(
                Multi_Scale_Fire4(in_channels, int(out_channels / (2 * 4)), int(out_channels / (2 * 4))),
                Multi_Scale_Fire4(int(out_channels / (3)), int(out_channels / (4)), int(out_channels / (4))),  # 12,6,6
                nn.Softsign()
            )
        else:
            layer = nn.Sequential(
                Multi_Scale_Fire4(in_channels, int(out_channels / 4), int(out_channels / (4)))
            )
        # print(f"layer : {layer}")
        return layer

    def multiresblock_front(self, in_channels, out_channels, doubleF=False):
        if doubleF:
            layer = nn.Sequential(
                MultiResblock(in_channels, int(out_channels / 2), 1),
                MultiResblock(int(out_channels / 2), out_channels, 1),
                nn.Softsign()
            )
        else:
            layer = nn.Sequential(
                MultiResblock(in_channels, out_channels, 1)
            )
        return layer

    def multiresblock_dil_front(self, in_channels, out_channels, doubleF=False):
        # print("multiresblock_dil_front in_channels : {}, out_channels : {}".format(in_channels, out_channels))
        # print(f"doubleF : {doubleF}")
        if doubleF:
            layer = nn.Sequential(
                MultiResblock_dil(in_channels, int(out_channels / 2), 1),
                MultiResblock_dil(int(out_channels / 2), out_channels, 1),
                nn.Softsign()
            )
        else:
            layer = nn.Sequential(
                MultiResblock_dil(in_channels, out_channels, 1)
            )
        # print(f"layer : {layer}")
        return layer

    def res_front(self, in_channels, out_channels, doubleF=False):
        if doubleF:
            layer = nn.Sequential(
                ResCNN_block(in_channels, int(out_channels / 2)),
                ResCNN_block(int(out_channels / 2), out_channels),
                nn.Softsign()
            )
        else:
            layer = nn.Sequential(
                ResCNN_block(in_channels, out_channels)
            )
        # print(f"layer : {layer}")
        return layer

    def res_pre_front(self, in_channels, out_channels, doubleF=False):
        if doubleF:
            layer = nn.Sequential(
                ResCNN_pre_block(in_channels, int(out_channels / 2)),
                ResCNN_pre_block(int(out_channels / 2), out_channels),
                nn.Softsign()
            )
        else:
            layer = nn.Sequential(
                ResCNN_pre_block(in_channels, out_channels)
            )
        # print(f"layer : {layer}")
        return layer

    def rec_front(self, in_channels, out_channels, doubleF=False):
        if doubleF:
            layer = nn.Sequential(
                RCNN_block(in_channels, int(out_channels / 2)),
                RCNN_block(int(out_channels / 2), out_channels),
                nn.Softsign()
            )
        else:
            layer = nn.Sequential(
                RCNN_block(in_channels, out_channels, 1)
            )
        # print(f"layer : {layer}")
        return layer

    def rec_pre_front(self, in_channels, out_channels, doubleF=False):
        if doubleF:
            layer = nn.Sequential(
                RCNN_pre_block(in_channels, int(out_channels / 2)),
                RCNN_pre_block(int(out_channels / 2), out_channels),
                nn.Softsign()
            )
        else:
            layer = nn.Sequential(
                RCNN_pre_block(in_channels, out_channels, 1)
            )
        # print(f"layer : {layer}")
        return layer

    def r2_front(self, in_channels, out_channels, doubleF=False):
        if doubleF:
            layer = nn.Sequential(
                RRCNN_block(in_channels, int(out_channels / 2)),
                RRCNN_block(int(out_channels / 2), out_channels),
                nn.Softsign()
            )
        else:
            layer = nn.Sequential(
                RRCNN_block(in_channels, out_channels)
            )
        # print(f"layer : {layer}")
        return layer

    def r2_pre_front(self, in_channels, out_channels, doubleF=False):
        if doubleF:
            layer = nn.Sequential(
                RRCNN_pre_block(in_channels, int(out_channels / 2)),
                RRCNN_pre_block(int(out_channels / 2), out_channels),
                nn.Softsign()
            )
        else:
            layer = nn.Sequential(
                RRCNN_pre_block(in_channels, out_channels)
            )
        # print(f"layer : {layer}")
        return layer

    def rsab_front(self, in_channels, out_channels, doubleF=False):
        if doubleF:
            layer = nn.Sequential(
                Res_drop_block(in_channels, int(out_channels / 2)),
                Res_drop_block(int(out_channels / 2), out_channels),
                # RSAB(out_channels, int(out_channels / 2))
                RSAB(out_channels, out_channels)
            )
        else:
            layer = nn.Sequential(
                Res_drop_block(in_channels, out_channels),
                # RSAB(out_channels, int(out_channels / 2))
                RSAB(out_channels, out_channels)
            )
        # print(f"layer : {layer}")
        return layer

    def resdrop_front(self, in_channels, out_channels, doubleF=False):
        if doubleF:
            layer = nn.Sequential(
                Res_drop_block(in_channels, int(out_channels / 2)),
                Res_drop_block(int(out_channels / 2), out_channels)
            )
        else:
            layer = nn.Sequential(
                Res_drop_block(in_channels, out_channels)
            )
        # print(f"layer : {layer}")
        return layer

    def decoder(self, in_channels, out_channels, kernel_size=2, stride=2, padding=0,
                output_padding=0, bias=True):
        layer = nn.Sequential(
            nn.ConvTranspose3d(in_channels, out_channels, kernel_size, stride=stride,
                               padding=padding, output_padding=output_padding, bias=bias),
            nn.ReLU())
        return layer

    def outputs(self, in_channels, out_channels, kernel_size=3, stride=1, padding=0,
                bias=False, doubleB=False):
        # print("outputs in_channels : {}, out_channels : {}".format(in_channels, out_channels))
        # print(f"doubleB : {doubleB}")
        if doubleB:
            layer = nn.Sequential(
                nn.Conv3d(in_channels, int(in_channels / 2), kernel_size, stride=stride, padding=padding, bias=bias),
                nn.LeakyReLU(0.2),
                nn.Conv3d(int(in_channels / 2), out_channels, kernel_size, stride=stride, padding=padding, bias=bias),
                nn.Softsign())
        else:
            layer = nn.Sequential(
                nn.Conv3d(in_channels, out_channels, kernel_size, stride=stride, padding=padding, bias=bias),
                nn.BatchNorm3d(out_channels),
                nn.Tanh())
        return layer

    def fire_back(self, in_channels, out_channels, doubleB=False):
        # print("fire_back in_channels : {}, out_channels : {}".format(in_channels,out_channels))
        # print(f"doubleB : {doubleB}")
        if doubleB:
            layer = nn.Sequential(
                Multi_Scale_Fire4(in_channels, int(in_channels / (2 * 4)), int(in_channels / (2 * 4))),
                Multi_Scale_Fire3(int(in_channels / 2), out_channels, 1),
                nn.Softsign())
        else:
            layer = nn.Sequential(
                Multi_Scale_Fire3(in_channels, out_channels, 1))
        return layer

    def multiresblock_dil_back(self, in_channels, out_channels, doubleB=False):
        # print("multiresblock_dil_back in_channels : {}, out_channels : {}".format(in_channels,out_channels))
        # print(f"doubleB : {doubleB}")
        if doubleB:
            layer = nn.Sequential(
                MultiResblock_dil(in_channels, int(in_channels / 2), 1),
                MultiResblock_dil(int(in_channels / 2), out_channels, 1),
                nn.Softsign())
        else:
            layer = nn.Sequential(
                MultiResblock_dil(in_channels, out_channels, 1))

        return layer

    def multiresblock_back(self, in_channels, out_channels, doubleB=False):
        if doubleB:
            layer = nn.Sequential(
                MultiResblock(in_channels, int(in_channels / 2), 1),
                MultiResblock(int(in_channels / 2), out_channels, 1),
                nn.Softsign())
        else:
            layer = nn.Sequential(
                MultiResblock(in_channels, out_channels, 1),
            )
        # print(f"layer : {layer}")
        return layer

    def res_back(self, in_channels, out_channels, doubleB=False):
        if doubleB:
            layer = nn.Sequential(
                ResCNN_block(in_channels, int(out_channels / 2)),
                ResCNN_block(int(out_channels / 2), out_channels),
                nn.Softsign()
            )
        else:
            layer = nn.Sequential(
                ResCNN_block(in_channels, out_channels)
            )
        # print(f"layer : {layer}")
        return layer

    def res_pre_back(self, in_channels, out_channels, doubleB=False):
        if doubleB:
            layer = nn.Sequential(
                ResCNN_pre_block(in_channels, int(out_channels / 2)),
                ResCNN_pre_block(int(out_channels / 2), out_channels),
                nn.Softsign()
            )
        else:
            layer = nn.Sequential(
                ResCNN_pre_block(in_channels, out_channels)
            )
        # print(f"layer : {layer}")
        return layer

    def rec_back(self, in_channels, out_channels, doubleB=False):
        if doubleB:
            layer = nn.Sequential(
                RCNN_block(in_channels, int(out_channels / 2)),
                RCNN_block(int(out_channels / 2), out_channels),
                nn.Softsign()
            )
        else:
            layer = nn.Sequential(
                RCNN_block(in_channels, out_channels)
            )
        # print(f"layer : {layer}")
        return layer

    def rec_pre_back(self, in_channels, out_channels, doubleB=False):
        if doubleB:
            layer = nn.Sequential(
                RCNN_pre_block(in_channels, int(out_channels / 2)),
                RCNN_pre_block(int(out_channels / 2), out_channels),
                nn.Softsign()
            )
        else:
            layer = nn.Sequential(
                RCNN_pre_block(in_channels, out_channels)
            )
        # print(f"layer : {layer}")
        return layer

    def r2_back(self, in_channels, out_channels, doubleB=False):
        if doubleB:
            layer = nn.Sequential(
                RRCNN_block(in_channels, int(out_channels / 2)),
                RRCNN_block(int(out_channels / 2), out_channels),
                nn.Softsign()
            )
        else:
            layer = nn.Sequential(
                RRCNN_block(in_channels, out_channels)
            )
        # print(f"layer : {layer}")
        return layer

    def r2_pre_back(self, in_channels, out_channels, doubleB=False):
        if doubleB:
            layer = nn.Sequential(
                RRCNN_pre_block(in_channels, int(out_channels / 2)),
                RRCNN_pre_block(int(out_channels / 2), out_channels),
                nn.Softsign()
            )
        else:
            layer = nn.Sequential(
                RRCNN_pre_block(in_channels, out_channels)
            )
        # print(f"layer : {layer}")
        return layer

    def rsab_back(self, in_channels, out_channels, doubleB=False):
        if doubleB:
            layer = nn.Sequential(
                Res_drop_block(in_channels, int(out_channels / 2)),
                Res_drop_block(int(out_channels / 2), out_channels),
                # RSAB(out_channels, int(out_channels / 2))
                RSAB(out_channels, out_channels)
            )
        else:
            layer = nn.Sequential(
                Res_drop_block(in_channels, out_channels),
                # RSAB(out_channels, int(out_channels / 2))
                RSAB(out_channels, out_channels)
            )
        # print(f"layer : {layer}")
        return layer

    def resdrop_back(self, in_channels, out_channels, doubleB=False):
        if doubleB:
            layer = nn.Sequential(
                Res_drop_block(in_channels, int(out_channels / 2)),
                Res_drop_block(int(out_channels / 2), out_channels)
            )
        else:
            layer = nn.Sequential(
                Res_drop_block(in_channels, out_channels)
            )
        # print(f"layer : {layer}")
        return layer

    def forward(self, x, y):
        # print(f'\t\tl1 x.shape : {x.shape}') #torch.Size([1, 1, 144, 160, 192])
        # print(f'\t\tl1 y.shape : {y.shape}') #torch.Size([1, 1, 144, 160, 192])


        x_down = self.down_avg(x)
        y_down = self.down_avg(y)

        x_down2 = self.down_avg(x_down)
        y_down2 = self.down_avg(y_down)
        # print(f'\t\tl1 x_down.shape : {x_down.shape}') #torch.Size([1, 1, 72, 80, 96])
        # print(f'\t\tl1 y_down.shape : {y_down.shape}') #torch.Size([1, 1, 72, 80, 96])
        # print(f'\t\tl1 x_down2.shape : {x_down2.shape}') #torch.Size([1, 1, 36, 40, 48])
        # print(f'\t\tl1 y_down2.shape : {y_down2.shape}') #torch.Size([1, 1, 36, 40, 48])




        fea_e0_x = self.input_encoder_lvl1(x_down2)
        # print(f'\t\tl1 fea_e0_x.shape : {fea_e0_x.shape}')  # torch.Size([1, 12, 36, 40, 48])
        f_x = self.avgpool(fea_e0_x)
        # print(f'\t\tl1 f_x.shape : {f_x.shape}') #torch.Size([1, 12, 1, 1, 1])
        f_x = f_x.squeeze()
        # print(f'\t\tl1 f_x.shape : {f_x.shape}') #torch.Size([12])
        if self.batchsize == 1:
            f_x = f_x.unsqueeze(dim=0)
            # print(f'\t\tl1 f_x.shape : {f_x.shape}') #torch.Size([1, 12])
        f_x = self.linear_x(f_x)
        # print(f'\t\tl1 f_x.shape : {f_x.shape}') #torch.Size([1, 12])
        f_x = f_x / f_x.norm(dim=-1, keepdim=True)
        # print(f'\t\tl1 f_x.shape : {f_x.shape}') #torch.Size([1, 12])

        fea_e0_y = self.input_encoder_lvl1(y_down2)
        # print(f'\t\tl1 fea_e0_y.shape : {fea_e0_y.shape}')  # torch.Size([1, 12, 36, 40, 48])
        f_y = self.avgpool(fea_e0_y)
        # print(f'\t\tl1 f_y.shape : {f_y.shape}') #torch.Size([1, 12, 1, 1, 1])
        f_y = f_y.squeeze()
        # print(f'\t\tl1 f_y.shape : {f_y.shape}') #torch.Size([12])
        if self.batchsize == 1:
            f_y = f_y.unsqueeze(dim=0)
            # print(f'\t\tl1 f_y.shape : {f_y.shape}') #torch.Size([1, 12])
        f_y = self.linear_x(f_y)
        # print(f'\t\tl1 f_y.shape : {f_y.shape}') #torch.Size([1, 12])
        f_y = f_y / f_y.norm(dim=-1, keepdim=True)
        # print(f'\t\tl1 f_y.shape : {f_y.shape}') #torch.Size([1, 12])



        fea_e0 = torch.cat((fea_e0_x, fea_e0_y), 1) #attention에 들어감
        # print(f'\t\tl1 fea_e0.shape : {fea_e0.shape}') #torch.Size([1, 24, 36, 40, 48])


        e0_x = self.down_conv(fea_e0_x)
        e0_y = self.down_conv(fea_e0_y)
        # print(f'\t\tl1 e0_x.shape : {e0_x.shape}') #torch.Size([1, 12, 18, 20, 24])
        # print(f'\t\tl1 e0_y.shape : {e0_y.shape}') #torch.Size([1, 12, 18, 20, 24])


        e0 = torch.cat((e0_x, e0_y), 1)
        # print(f'\t\tl1 e0.shape : {e0.shape}') #torch.Size([1, 24, 18, 20, 24])

        e0 = self.resblock_group_lvl1(e0)
        # print(f'\t\tl1 e0.shape resblock_group_lvl1: {e0.shape}') #torch.Size([1, 24, 18, 20, 24])
        e0 = self.up(e0)
        # print(f'\t\tl1 e0.shape up: {e0.shape}') #torch.Size([1, 12, 36, 40, 48])
        attn = self.attention(e0, fea_e0)
        # print(f"\t\tl1 attn.shape : {attn.shape}") #torch.Size([1, 24, 36, 40, 48])

        if self.concat == 'fea_e0':
            output_disp_e0_v = self.output_lvl1(torch.cat([attn, fea_e0], dim=1)) * self.range_flow
        elif self.concat == 'e0':
            output_disp_e0_v = self.output_lvl1(torch.cat([attn, e0], dim=1)) * self.range_flow

        # print(f"\t\tl1 output_disp_e0_v.shape : {output_disp_e0_v.shape}") #torch.Size([1, 3, 36, 40, 48])

        output_disp_e0 = self.diff_transform(output_disp_e0_v, self.grid_1)
        # print(f"\t\tl1 output_disp_e0.shape : {output_disp_e0.shape}") #torch.Size([1, 3, 36, 40, 48])
        warpped_inputx_lvl1_out = self.transform(x, output_disp_e0.permute(0, 2, 3, 4, 1), self.grid_1)
        # print(f"\t\tl1 warpped_inputx_lvl1_out.shape : {warpped_inputx_lvl1_out.shape}") #torch.Size([1, 3, 36, 40, 48])

        if self.is_train is True:
            return output_disp_e0, warpped_inputx_lvl1_out, y_down2, output_disp_e0_v, e0, f_x, f_y
            # return output_disp_e0, warpped_inputx_lvl1_out, output_disp_e0_v, e0, f_x, f_y
        else:
            return output_disp_e0



class model_diff_l2(nn.Module):
    def __init__(self, in_channel, ch_start, ch_start_magnitude, n_classes, is_train=True, imgshape=(160, 192, 144), range_flow=0.4,
                 model_lvl1=None, model_name_front='unet_diff', model_name_back='both', doubleF=True, doubleB=True, batchsize=1,
                 attn='attn',attn_batch = True, attn_modi_multiple = True, concat='fea_e0'):
        super(model_diff_l2, self).__init__()

        self.in_channel = in_channel
        self.n_classes = n_classes
        self.ch_start = ch_start
        self.ch_start_magnitude = ch_start_magnitude

        self.model_name_front = model_name_front
        if model_name_back == 'both':
            self.model_name_back = model_name_front
            # print("diff l2 self.model_name_back : ", self.model_name_back)
        else:
            self.model_name_back = model_name_back
            # print("diff l2 self.model_name_back : ", self.model_name_back)
        self.doubleF = doubleF
        self.doubleB = doubleB

        self.attn = attn
        self.attn_batch = attn_batch
        # self.attn_mid_ch = attn_mid_ch
        self.attn_modi_multiple = attn_modi_multiple

        self.concat = concat
        if self.concat == 'e0':
            self.factor = 3
        elif self.concat == 'fea_e0':
            self.factor = 4

        self.batchsize = batchsize

        self.avgpool = torch.nn.AdaptiveAvgPool3d((1, 1, 1))
        self.linear_x = torch.nn.Linear(self.ch_start * self.ch_start_magnitude, self.ch_start * self.ch_start_magnitude)
        self.linear_y = torch.nn.Linear(self.ch_start * self.ch_start_magnitude, self.ch_start * self.ch_start_magnitude)

        self.range_flow = range_flow
        self.is_train = is_train

        self.imgshape = imgshape

        self.model_lvl1 = model_lvl1

        self.grid_1 = generate_grid_unit(self.imgshape)
        self.grid_1 = torch.from_numpy(np.reshape(self.grid_1, (1,) + self.grid_1.shape)).to(DEVICE).float()

        self.diff_transform = DiffeomorphicTransform_unit(time_step=7).to(DEVICE)
        self.transform = SpatialTransform_unit().to(DEVICE)

        bias_opt = False

        if self.model_name_front == 'unet_diff':
            self.input_encoder_lvl1 = self.input_feature_extract(self.in_channel//2 + 3, self.ch_start * self.ch_start_magnitude,
                                                                 bias=bias_opt, doubleF=self.doubleF)

        elif self.model_name_front == 'MSF_diff':
            self.input_encoder_lvl1 = self.fire_front(self.in_channel//2+3, self.ch_start * self.ch_start_magnitude, doubleF=self.doubleF)

        elif self.model_name_front == 'MR_diff':
            self.input_encoder_lvl1 = self.multiresblock_front(self.in_channel//2+3, self.ch_start * self.ch_start_magnitude,
                                                               doubleF=self.doubleF)

        elif self.model_name_front == 'MRD_diff':
            self.input_encoder_lvl1 = self.multiresblock_dil_front(self.in_channel//2+3, self.ch_start * self.ch_start_magnitude,
                                                                   doubleF=self.doubleF)
        elif self.model_name_front == 'Res_diff':
            self.input_encoder_lvl1 = self.res_front(self.in_channel//2+3, self.ch_start * self.ch_start_magnitude,
                                                     doubleF=self.doubleF)

        elif self.model_name_front == 'Rec_diff':
            self.input_encoder_lvl1 = self.rec_front(self.in_channel//2+3, self.ch_start * self.ch_start_magnitude,
                                                     doubleF=self.doubleF)

        elif self.model_name_front == 'R2_diff':
            self.input_encoder_lvl1 = self.r2_front(self.in_channel//2+3, self.ch_start * self.ch_start_magnitude,
                                                    doubleF=self.doubleF)

        elif self.model_name_front == 'Res_pre_diff':
            self.input_encoder_lvl1 = self.res_pre_front(self.in_channel//2+3, self.ch_start * self.ch_start_magnitude,
                                                         doubleF=self.doubleF)

        elif self.model_name_front == 'Rec_pre_diff':
            self.input_encoder_lvl1 = self.rec_pre_front(self.in_channel//2+3, self.ch_start * self.ch_start_magnitude,
                                                         doubleF=self.doubleF)

        elif self.model_name_front == 'R2_pre_diff':
            self.input_encoder_lvl1 = self.r2_pre_front(self.in_channel//2+3, self.ch_start * self.ch_start_magnitude,
                                                        doubleF=self.doubleF)

        elif self.model_name_front == 'RSAB_diff':
            self.input_encoder_lvl1 = self.rsab_front(self.in_channel//2+3, self.ch_start * self.ch_start_magnitude,
                                                      doubleF=self.doubleF)
        elif self.model_name_front == 'ResDrop_diff':
            self.input_encoder_lvl1 = self.resdrop_front(self.in_channel//2+3, self.ch_start * self.ch_start_magnitude,
                                                         doubleF=self.doubleF)


        self.down_conv = nn.Conv3d(self.ch_start * ch_start_magnitude, self.ch_start * ch_start_magnitude, 3, stride=2, padding=1, bias=bias_opt)

        self.resblock_group_lvl1 = self.resblock_seq(self.ch_start * ch_start_magnitude*2, bias_opt=bias_opt)

        self.up_tri = torch.nn.Upsample(scale_factor=2, mode="trilinear", align_corners=True)#align_corners=False




        self.up = nn.ConvTranspose3d(self.ch_start * ch_start_magnitude*2, self.ch_start * ch_start_magnitude, 2, stride=2,
                                     padding=0, output_padding=0, bias=bias_opt)

        if self.attn == 'attn':
            self.attention = Attention_block(self.ch_start * self.ch_start_magnitude, self.ch_start * self.ch_start_magnitude*2, self.ch_start * self.ch_start_magnitude*2, self.attn_batch)

        elif self.attn =='attn_w_Dil':
            self.attention = Attn_w_Dil(self.ch_start * self.ch_start_magnitude, self.ch_start * self.ch_start_magnitude*2, self.ch_start * self.ch_start_magnitude*2, self.attn_batch)

        elif self.attn == 'multi_attn':
            self.attention = MultiAttention(self.ch_start * self.ch_start_magnitude, self.ch_start * self.ch_start_magnitude*2,
                                                           self.ch_start * self.ch_start_magnitude*2, self.attn_batch, multiple=self.attn_modi_multiple)



        self.down_avg = nn.AvgPool3d(kernel_size=3, stride=2, padding=1, count_include_pad=False)

        if self.model_name_back == 'unet_diff':
            self.output_lvl1 = self.outputs(self.ch_start * ch_start_magnitude*self.factor, self.n_classes, kernel_size=3, stride=1, padding=1, bias=False, doubleB = self.doubleB)

        elif self.model_name_back == 'MSF_diff':
            self.output_lvl1 =self.fire_back(self.ch_start * ch_start_magnitude*self.factor, self.n_classes, doubleB=self.doubleB)

        elif self.model_name_back == 'MR_diff':
            self.output_lvl1 =self.multiresblock_back(self.ch_start * ch_start_magnitude*self.factor, self.n_classes, doubleB=self.doubleB)

        elif self.model_name_back == 'MRD_diff':
            self.output_lvl1 = self.multiresblock_dil_back(self.ch_start * ch_start_magnitude*self.factor, self.n_classes, doubleB=self.doubleB)
        elif self.model_name_back == 'Res_diff':
            self.output_lvl1 = self.res_back(self.ch_start * self.ch_start_magnitude*self.factor, self.n_classes, doubleB=self.doubleB)

        elif self.model_name_back == 'Rec_diff':
            self.output_lvl1 = self.rec_back(self.ch_start * self.ch_start_magnitude*self.factor, self.n_classes, doubleB=self.doubleB)

        elif self.model_name_back == 'R2_diff':
            self.output_lvl1 = self.r2_back(self.ch_start * self.ch_start_magnitude*self.factor, self.n_classes, doubleB=self.doubleB)

        elif self.model_name_back == 'Res_pre_diff':
            self.output_lvl1 = self.res_pre_back(self.ch_start * self.ch_start_magnitude*self.factor, self.n_classes, doubleB=self.doubleB)

        elif self.model_name_back == 'Rec_pre_diff':
            self.output_lvl1 = self.rec_pre_back(self.ch_start * self.ch_start_magnitude*self.factor, self.n_classes, doubleB=self.doubleB)

        elif self.model_name_back == 'R2_pre_diff':
            self.output_lvl1 = self.r2_pre_back(self.ch_start * self.ch_start_magnitude*self.factor, self.n_classes, doubleB=self.doubleB)

        elif self.model_name_back == 'RSAB_diff':
            self.output_lvl1 = self.rsab_back(self.ch_start * self.ch_start_magnitude*self.factor, self.n_classes, doubleB=self.doubleB)
        elif self.model_name_back == 'ResDrop_diff':
            self.output_lvl1 = self.resdrop_back(self.ch_start * self.ch_start_magnitude*self.factor, self.n_classes, doubleB=self.doubleB)


    def unfreeze_modellvl1(self):
        # unFreeze model_lvl1 weight
        print("\nunfreeze model_lvl1 parameter")
        for param in self.model_lvl1.parameters():
            param.requires_grad = True

    def resblock_seq(self, in_channels, bias_opt=False):
        layer = nn.Sequential(
            PreActBlock(in_channels, in_channels, bias=bias_opt),
            nn.LeakyReLU(0.2),
            PreActBlock(in_channels, in_channels, bias=bias_opt),
            nn.LeakyReLU(0.2),
            PreActBlock(in_channels, in_channels, bias=bias_opt),
            nn.LeakyReLU(0.2),
            PreActBlock(in_channels, in_channels, bias=bias_opt),
            nn.LeakyReLU(0.2),
            PreActBlock(in_channels, in_channels, bias=bias_opt),
            nn.LeakyReLU(0.2)
        )
        return layer

    def input_feature_extract(self, in_channels, out_channels, kernel_size=3, stride=1, padding=1,
                              bias=False, doubleF=False):
        # print("input_feature_extract in_channels : {}, out_channels : {}".format(in_channels, out_channels))
        # print(f"doubleF : {doubleF}")
        if doubleF:
            layer = nn.Sequential(
                nn.Conv3d(in_channels, out_channels, kernel_size, stride=stride, padding=padding, bias=bias),
                nn.LeakyReLU(0.2),
                nn.Conv3d(out_channels, out_channels, kernel_size, stride=stride, padding=padding, bias=bias))

        else:
            layer = nn.Sequential(
                nn.Conv3d(in_channels, out_channels, kernel_size, stride=stride, padding=padding, bias=bias),
                nn.BatchNorm3d(out_channels),
                nn.ReLU())
        # print(f"layer : {layer}")
        return layer

    def fire_front(self, in_channels, out_channels, doubleF=False):
        # print("fire_front in_channels : {}, out_channels : {}".format(in_channels, out_channels))
        # print(f"doubleF : {doubleF}")
        if doubleF:
            layer = nn.Sequential(
                Multi_Scale_Fire4(in_channels, int(out_channels / (2 * 4)), int(out_channels / (2 * 4))), #2,3,3
                Multi_Scale_Fire4(int(out_channels / (3)), int(out_channels / (4)), int(out_channels / (4))),  # 12,6,6
                # Multi_Scale_Fire4(int(out_channels / (2)), int(out_channels / (2 * 4)), int(out_channels/(4))),#12,3,6
                # Multi_Scale_Fire3(int(out_channels / (2*2)), 3, out_channels/4),
                nn.Softsign()
            )
        else:
            layer = nn.Sequential(
                Multi_Scale_Fire4(in_channels, int(out_channels / 4), int(out_channels/(4)))
            )
        # print(f"layer : {layer}")
        return layer


    def multiresblock_front(self, in_channels, out_channels, doubleF=False):
        # print("multiresblock_front in_channels : {}, out_channels : {}".format(in_channels, out_channels))
        # print(f"doubleF : {doubleF}")
        if doubleF:
            # def __init__(self, num_in_channels, num_filters, alpha=1.67):
            layer = nn.Sequential(
                MultiResblock(in_channels, int(out_channels / 2), 1),
                MultiResblock(int(out_channels / 2), out_channels, 1),
                nn.Softsign()
            )
        else:
            layer = nn.Sequential(
                MultiResblock(in_channels, out_channels, 1)
            )
        # print(f"layer : {layer}")
        return layer

    def multiresblock_dil_front(self, in_channels, out_channels, doubleF=False):
        # print("multiresblock_dil_front in_channels : {}, out_channels : {}".format(in_channels, out_channels))
        # print(f"doubleF : {doubleF}")
        if doubleF:
            layer = nn.Sequential(
                MultiResblock_dil(in_channels, int(out_channels / 2), 1),
                MultiResblock_dil(int(out_channels / 2), out_channels, 1),
                nn.Softsign()
            )
        else:
            layer = nn.Sequential(
                MultiResblock_dil(in_channels, out_channels, 1)
            )
        # print(f"layer : {layer}")
        return layer

    def res_front(self, in_channels, out_channels, doubleF=False):
        if doubleF:
            layer = nn.Sequential(
                ResCNN_block(in_channels, int(out_channels / 2)),
                ResCNN_block(int(out_channels / 2), out_channels),
                nn.Softsign()
            )
        else:
            layer = nn.Sequential(
                ResCNN_block(in_channels, out_channels)
            )
        # print(f"layer : {layer}")
        return layer

    def res_pre_front(self, in_channels, out_channels, doubleF=False):
        if doubleF:
            layer = nn.Sequential(
                ResCNN_pre_block(in_channels, int(out_channels / 2)),
                ResCNN_pre_block(int(out_channels / 2), out_channels),
                nn.Softsign()
            )
        else:
            layer = nn.Sequential(
                ResCNN_pre_block(in_channels, out_channels)
            )
        # print(f"layer : {layer}")
        return layer

    def rec_front(self, in_channels, out_channels, doubleF=False):
        if doubleF:
            layer = nn.Sequential(
                RCNN_block(in_channels, int(out_channels / 2)),
                RCNN_block(int(out_channels / 2), out_channels),
                nn.Softsign()
            )
        else:
            layer = nn.Sequential(
                RCNN_block(in_channels, out_channels, 1)
            )
        # print(f"layer : {layer}")
        return layer

    def rec_pre_front(self, in_channels, out_channels, doubleF=False):
        if doubleF:
            layer = nn.Sequential(
                RCNN_pre_block(in_channels, int(out_channels / 2)),
                RCNN_pre_block(int(out_channels / 2), out_channels),
                nn.Softsign()
            )
        else:
            layer = nn.Sequential(
                RCNN_pre_block(in_channels, out_channels, 1)
            )
        # print(f"layer : {layer}")
        return layer

    def r2_front(self, in_channels, out_channels, doubleF=False):
        if doubleF:
            layer = nn.Sequential(
                RRCNN_block(in_channels, int(out_channels / 2)),
                RRCNN_block(int(out_channels / 2), out_channels),
                nn.Softsign()
            )
        else:
            layer = nn.Sequential(
                RRCNN_block(in_channels, out_channels)
            )
        # print(f"layer : {layer}")
        return layer

    def r2_pre_front(self, in_channels, out_channels, doubleF=False):
        if doubleF:
            layer = nn.Sequential(
                RRCNN_pre_block(in_channels, int(out_channels / 2)),
                RRCNN_pre_block(int(out_channels / 2), out_channels),
                nn.Softsign()
            )
        else:
            layer = nn.Sequential(
                RRCNN_pre_block(in_channels, out_channels)
            )
        # print(f"layer : {layer}")
        return layer

    def rsab_front(self, in_channels, out_channels, doubleF=False):
        if doubleF:
            layer = nn.Sequential(
                Res_drop_block(in_channels, int(out_channels / 2)),
                Res_drop_block(int(out_channels / 2), out_channels),
                # RSAB(out_channels, int(out_channels / 2))
                RSAB(out_channels, out_channels)
            )
        else:
            layer = nn.Sequential(
                Res_drop_block(in_channels, out_channels),
                # RSAB(out_channels, int(out_channels / 2))
                RSAB(out_channels, out_channels)
            )
        # print(f"layer : {layer}")
        return layer

    def resdrop_front(self, in_channels, out_channels, doubleF=False):
        if doubleF:
            layer = nn.Sequential(
                Res_drop_block(in_channels, int(out_channels / 2)),
                Res_drop_block(int(out_channels / 2), out_channels)
            )
        else:
            layer = nn.Sequential(
                Res_drop_block(in_channels, out_channels)
            )
        # print(f"layer : {layer}")
        return layer

    def decoder(self, in_channels, out_channels, kernel_size=2, stride=2, padding=0,
                output_padding=0, bias=True):
        layer = nn.Sequential(
            nn.ConvTranspose3d(in_channels, out_channels, kernel_size, stride=stride,
                               padding=padding, output_padding=output_padding, bias=bias),
            nn.ReLU())
        return layer

    def outputs(self, in_channels, out_channels, kernel_size=3, stride=1, padding=0,
                bias=False, doubleB=False):
        # print("outputs in_channels : {}, out_channels : {}".format(in_channels, out_channels))
        # print(f"doubleB : {doubleB}")
        if doubleB:
            layer = nn.Sequential(
                nn.Conv3d(in_channels, int(in_channels / 2), kernel_size, stride=stride, padding=padding, bias=bias),
                nn.LeakyReLU(0.2),
                nn.Conv3d(int(in_channels / 2), out_channels, kernel_size, stride=stride, padding=padding, bias=bias),
                nn.Softsign())
        else:
            layer = nn.Sequential(
                nn.Conv3d(in_channels, out_channels, kernel_size, stride=stride, padding=padding, bias=bias),
                nn.BatchNorm3d(out_channels),
                nn.Tanh())
        # print(f"layer : {layer}")
        return layer

    def fire_back(self, in_channels, out_channels, doubleB=False):
        # print("fire_back in_channels : {}, out_channels : {}".format(in_channels,out_channels))
        # print(f"doubleB : {doubleB}")
        if doubleB:
            layer = nn.Sequential(
                Multi_Scale_Fire4(in_channels, int(in_channels / (2*4)), int(in_channels / (2*4))),
                # nn.LeakyReLU(0.2),
                Multi_Scale_Fire3(int(in_channels / 2), out_channels, 1),
                nn.Softsign()
            )
        else:
            layer = nn.Sequential(
                Multi_Scale_Fire3(in_channels, out_channels, 1)

            )
        # print(f"layer : {layer}")
        return layer

    def multiresblock_dil_back(self, in_channels, out_channels, doubleB=False):
        # print("multiresblock_dil_back in_channels : {}, out_channels : {}".format(in_channels,out_channels))
        # print(f"doubleB : {doubleB}")
        if doubleB:
            layer = nn.Sequential(
                MultiResblock_dil(in_channels, int(in_channels / 2), 1),
                # nn.LeakyReLU(0.2),
                MultiResblock_dil(int(in_channels / 2), out_channels, 1),
                nn.Softsign()
            )
        else:
            layer = nn.Sequential(
                MultiResblock_dil(in_channels, out_channels, 1)
            )
        # print(f"layer : {layer}")
        return layer

    def multiresblock_back(self, in_channels, out_channels, doubleB=False):
        # print("multiresblock_back in_channels : {}, out_channels : {}".format(in_channels, out_channels))
        # print(f"doubleB : {doubleB}")
        if doubleB:
            layer = nn.Sequential(
                MultiResblock(in_channels, int(in_channels / 2), 1),
                # nn.LeakyReLU(0.2),
                MultiResblock(int(in_channels / 2), out_channels, 1),
                nn.Softsign()
            )
        else:
            layer = nn.Sequential(
                MultiResblock(in_channels, out_channels, 1)
            )
        # print(f"layer : {layer}")
        return layer

    def res_back(self, in_channels, out_channels, doubleB=False):
        if doubleB:
            layer = nn.Sequential(
                ResCNN_block(in_channels, int(out_channels / 2)),
                ResCNN_block(int(out_channels / 2), out_channels),
                nn.Softsign()
            )
        else:
            layer = nn.Sequential(
                ResCNN_block(in_channels, out_channels)
            )
        # print(f"layer : {layer}")
        return layer

    def res_pre_back(self, in_channels, out_channels, doubleB=False):
        if doubleB:
            layer = nn.Sequential(
                ResCNN_pre_block(in_channels, int(out_channels / 2)),
                ResCNN_pre_block(int(out_channels / 2), out_channels),
                nn.Softsign()
            )
        else:
            layer = nn.Sequential(
                ResCNN_pre_block(in_channels, out_channels)
            )
        # print(f"layer : {layer}")
        return layer

    def rec_back(self, in_channels, out_channels, doubleB=False):
        if doubleB:
            layer = nn.Sequential(
                RCNN_block(in_channels, int(out_channels / 2)),
                RCNN_block(int(out_channels / 2), out_channels),
                nn.Softsign()
            )
        else:
            layer = nn.Sequential(
                RCNN_block(in_channels, out_channels)
            )
        # print(f"layer : {layer}")
        return layer

    def rec_pre_back(self, in_channels, out_channels, doubleB=False):
        if doubleB:
            layer = nn.Sequential(
                RCNN_pre_block(in_channels, int(out_channels / 2)),
                RCNN_pre_block(int(out_channels / 2), out_channels),
                nn.Softsign()
            )
        else:
            layer = nn.Sequential(
                RCNN_pre_block(in_channels, out_channels)
            )
        # print(f"layer : {layer}")
        return layer

    def r2_back(self, in_channels, out_channels, doubleB=False):
        if doubleB:
            layer = nn.Sequential(
                RRCNN_block(in_channels, int(out_channels / 2)),
                RRCNN_block(int(out_channels / 2), out_channels),
                nn.Softsign()
            )
        else:
            layer = nn.Sequential(
                RRCNN_block(in_channels, out_channels)
            )
        # print(f"layer : {layer}")
        return layer

    def r2_pre_back(self, in_channels, out_channels, doubleB=False):
        if doubleB:
            layer = nn.Sequential(
                RRCNN_pre_block(in_channels, int(out_channels / 2)),
                RRCNN_pre_block(int(out_channels / 2), out_channels),
                nn.Softsign()
            )
        else:
            layer = nn.Sequential(
                RRCNN_pre_block(in_channels, out_channels)
            )
        # print(f"layer : {layer}")
        return layer

    def rsab_back(self, in_channels, out_channels, doubleB=False):
        if doubleB:
            layer = nn.Sequential(
                Res_drop_block(in_channels, int(out_channels / 2)),
                Res_drop_block(int(out_channels / 2), out_channels),
                # RSAB(out_channels, int(out_channels / 2))
                RSAB(out_channels, out_channels)
            )
        else:
            layer = nn.Sequential(
                Res_drop_block(in_channels, out_channels),
                # RSAB(out_channels, int(out_channels / 2))
                RSAB(out_channels, out_channels)
            )
        # print(f"layer : {layer}")
        return layer

    def resdrop_back(self, in_channels, out_channels, doubleB=False):
        if doubleB:
            layer = nn.Sequential(
                Res_drop_block(in_channels, int(out_channels / 2)),
                Res_drop_block(int(out_channels / 2), out_channels)
            )
        else:
            layer = nn.Sequential(
                Res_drop_block(in_channels, out_channels)
            )
        # print(f"layer : {layer}")
        return layer

    def forward(self, x, y):
        # print(f'\t l2 x.shape : {x.shape}') #torch.Size([1, 1, 144, 160, 192])
        # print(f'\t l2 y.shape : {y.shape}') #torch.Size([1, 1, 144, 160, 192])
        #output_disp_e0, warpped_inputx_lvl1_out, output_disp_e0_v, e0
        lvl1_disp, _, _, lvl1_v, lvl1_embedding, f_x_l1, f_x_l2 = self.model_lvl1(x, y)


        # print()
        # print(f'\t l2 lvl1_disp.shape : {lvl1_disp.shape}') #torch.Size([1, 3, 36, 40, 48])
        # print(f'\t l2 lvl1_v.shape : {lvl1_v.shape}') #torch.Size([1, 3, 36, 40, 48])
        # print(f'\t l2 lvl1_embedding.shape : {lvl1_embedding.shape}') #torch.Size([1, 24, 36, 40, 48])


        lvl1_disp_up = self.up_tri(lvl1_disp)
        lvl1_v_up = self.up_tri(lvl1_v)
        # print(f'\t l2 lvl1_disp_up.shape : {lvl1_disp_up.shape}') #torch.Size([1, 3, 72, 80, 96])
        # print(f'\t l2 lvl1_v_up.shape : {lvl1_v_up.shape}') #torch.Size([1, 3, 72, 80, 96])

        x_down = self.down_avg(x)
        y_down = self.down_avg(y)
        # print(f'\t l2 x_down.shape : {x_down.shape}') #torch.Size([1, 1, 72, 80, 96])
        # print(f'\t l2 y_down.shape : {y_down.shape}') #torch.Size([1, 1, 72, 80, 96])


        warpped_x = self.transform(x_down, lvl1_disp_up.permute(0, 2, 3, 4, 1), self.grid_1)
        # print(f'\t l2 warpped_x.shape : {warpped_x.shape}') #torch.Size([1, 1, 72, 80, 96])

        cat_input_lvl2_x = torch.cat((warpped_x, lvl1_v_up), 1)
        # print(f'\t l2 cat_input_lvl2_x.shape : {cat_input_lvl2_x.shape}') #torch.Size([1, 4, 72, 80, 96])
        fea_e0_x = self.input_encoder_lvl1(cat_input_lvl2_x)
        # print(f'\t l2 fea_e0_x.shape : {fea_e0_x.shape}') #torch.Size([1, 12, 72, 80, 96])
        ####
        f_x = self.avgpool(fea_e0_x)
        # print(f'\t f_x.shape : {f_x.shape}')
        f_x = f_x.squeeze()
        # print(f'\t f_x.shape : {f_x.shape}')
        if self.batchsize == 1:
            f_x = f_x.unsqueeze(dim=0)
            # print(f'\t f_x.shape : {f_x.shape}')
        f_x = self.linear_x(f_x)
        # print(f'\t f_x.shape : {f_x.shape}')
        f_x = f_x / f_x.norm(dim=-1, keepdim=True)
        # print(f'\t f_x.shape : {f_x.shape}')

        cat_input_lvl2_y = torch.cat((y_down, lvl1_v_up), 1)
        fea_e0_y = self.input_encoder_lvl1(cat_input_lvl2_y)

        # print(f'\t l2 cat_input_lvl2_y.shape : {cat_input_lvl2_y.shape}') #torch.Size([1, 4, 72, 80, 96])
        # print(f'\t l2 fea_e0_y.shape : {fea_e0_y.shape}') #torch.Size([1, 12, 72, 80, 96])
        ####
        f_y = self.avgpool(fea_e0_y)
        # print(f'\t f_y.shape : {f_y.shape}')
        f_y = f_y.squeeze()
        # print(f'\t f_y.shape : {f_y.shape}')
        if self.batchsize == 1:
            f_y = f_y.unsqueeze(dim=0)
            # print(f'\t f_y.shape : {f_y.shape}')
        f_y = self.linear_y(f_y)
        # print(f'\t f_y.shape : {f_y.shape}')
        f_y = f_y / f_y.norm(dim=-1, keepdim=True)
        # print(f'\t f_y.shape : {f_y.shape}')

        e0_x = self.down_conv(fea_e0_x)
        e0_y = self.down_conv(fea_e0_y)
        # print(f'\t l2 e0_x.shape : {e0_x.shape}')
        # print(f'\t l2 e0_y.shape : {e0_y.shape}')



        e0_x = e0_x + lvl1_embedding
        e0_y = e0_y + lvl1_embedding
        e0 = torch.cat((e0_x, e0_y),1)
        # print(f'\t l2 e0.shape : {e0.shape}') #torch.Size([1, 24, 36, 40, 48])
        e0 = self.resblock_group_lvl1(e0)
        # print(f'\t l2 e0.shape after resblock_group_lvl1 : {e0.shape}') #torch.Size([1, 24, 36, 40, 48])
        e0 = self.up(e0)
        # print(f'\t l2 e0.shape after up : {e0.shape}') #torch.Size([1, 24, 72, 80, 96])

        fea_e0 = torch.cat((fea_e0_x, fea_e0_y),1)
        # print(f'\t l2 fea_e0.shape : {fea_e0.shape}') #torch.Size([1, 24, 72, 80, 96])
        attn = self.attention(e0, fea_e0)
        # print(f'\t l2 attn.shape : {attn.shape}') #torch.Size([1, 24, 72, 80, 96])


        # output_disp_e0_v = self.output_lvl1(torch.cat([attn, e0], dim=1)) * self.range_flow
        if self.concat == 'fea_e0':
            output_disp_e0_v = self.output_lvl1(torch.cat([attn, fea_e0], dim=1)) * self.range_flow
        elif self.concat == 'e0':
            output_disp_e0_v = self.output_lvl1(torch.cat([attn, e0], dim=1)) * self.range_flow
        # print(f'\t l2 output_disp_e0_v.shape : {output_disp_e0_v.shape}') #torch.Size([1, 3, 72, 80, 96])

        compose_field_e0_lvl1v = output_disp_e0_v + lvl1_v_up
        # print(f'\t l2 compose_field_e0_lvl1v.shape : {compose_field_e0_lvl1v.shape}')
        output_disp_e0 = self.diff_transform(compose_field_e0_lvl1v, self.grid_1)
        # print(f'\t l2 output_disp_e0.shape : {output_disp_e0.shape}')
        warpped_inputx_lvl1_out = self.transform(x, output_disp_e0.permute(0, 2, 3, 4, 1), self.grid_1)
        # print(f'\t l2 warpped_inputx_lvl1_out.shape : {warpped_inputx_lvl1_out.shape}')

        if self.is_train is True:
            # return output_disp_e0, warpped_inputx_lvl1_out, compose_field_e0_lvl1v, lvl1_v, e0, f_x, f_y
            return output_disp_e0, warpped_inputx_lvl1_out, y_down, compose_field_e0_lvl1v, lvl1_v, e0, f_x, f_y
        else:
            return output_disp_e0




class model_diff_l3(nn.Module):
    def __init__(self, in_channel, ch_start, ch_start_magnitude, n_classes, is_train=True, imgshape=(160, 192, 144), range_flow=0.4,
                 model_lvl2=None, model_name_front='unet_diff', model_name_back='both', doubleF=True, doubleB=True, batchsize=1,
                 attn='attn',attn_batch = True, attn_modi_multiple = True, concat='fea_e0'):
        super(model_diff_l3, self).__init__()

        self.in_channel = in_channel
        self.n_classes = n_classes
        self.ch_start = ch_start
        self.ch_start_magnitude = ch_start_magnitude

        self.model_name_front = model_name_front
        if model_name_back == 'both':
            self.model_name_back = model_name_front
        else:
            self.model_name_back = model_name_back
        self.doubleF = doubleF
        self.doubleB = doubleB

        self.attn = attn
        self.attn_batch = attn_batch
        # self.attn_mid_ch = attn_mid_ch
        self.attn_modi_multiple = attn_modi_multiple

        self.concat = concat
        if self.concat == 'e0':
            self.factor = 3
        elif self.concat == 'fea_e0':
            self.factor = 4



        self.batchsize = batchsize

        self.avgpool = torch.nn.AdaptiveAvgPool3d((1, 1, 1))
        self.linear_x = torch.nn.Linear(self.ch_start * self.ch_start_magnitude,
                                        self.ch_start * self.ch_start_magnitude)
        self.linear_y = torch.nn.Linear(self.ch_start * self.ch_start_magnitude,
                                        self.ch_start * self.ch_start_magnitude)

        self.range_flow = range_flow
        self.is_train = is_train

        self.imgshape = imgshape

        self.model_lvl2 = model_lvl2

        self.grid_1 = generate_grid_unit(self.imgshape)
        self.grid_1 = torch.from_numpy(np.reshape(self.grid_1, (1,) + self.grid_1.shape)).to(DEVICE).float()

        self.diff_transform = DiffeomorphicTransform_unit(time_step=7).to(DEVICE)
        self.transform = SpatialTransform_unit().to(DEVICE)

        bias_opt = False

        if self.model_name_front == 'unet_diff':
            self.input_encoder_lvl1 = self.input_feature_extract(self.in_channel // 2 + 3,
                                                                 self.ch_start * self.ch_start_magnitude,
                                                                 bias=bias_opt, doubleF=self.doubleF)

        elif self.model_name_front == 'MSF_diff':
            self.input_encoder_lvl1 = self.fire_front(self.in_channel // 2 + 3, self.ch_start * self.ch_start_magnitude,
                                                      doubleF=self.doubleF)

        elif self.model_name_front == 'MR_diff':
            self.input_encoder_lvl1 = self.multiresblock_front(self.in_channel // 2 + 3,
                                                               self.ch_start * self.ch_start_magnitude,
                                                               doubleF=self.doubleF)

        elif self.model_name_front == 'MRD_diff':
            self.input_encoder_lvl1 = self.multiresblock_dil_front(self.in_channel // 2 + 3,
                                                                   self.ch_start * self.ch_start_magnitude,
                                                                   doubleF=self.doubleF)
        elif self.model_name_front == 'Res_diff':
            self.input_encoder_lvl1 = self.res_front(self.in_channel // 2 + 3, self.ch_start * self.ch_start_magnitude,
                                                     doubleF=self.doubleF)

        elif self.model_name_front == 'Rec_diff':
            self.input_encoder_lvl1 = self.rec_front(self.in_channel // 2 + 3, self.ch_start * self.ch_start_magnitude,
                                                     doubleF=self.doubleF)

        elif self.model_name_front == 'R2_diff':
            self.input_encoder_lvl1 = self.r2_front(self.in_channel // 2 + 3, self.ch_start * self.ch_start_magnitude,
                                                    doubleF=self.doubleF)

        elif self.model_name_front == 'Res_pre_diff':
            self.input_encoder_lvl1 = self.res_pre_front(self.in_channel // 2 + 3,
                                                         self.ch_start * self.ch_start_magnitude,
                                                         doubleF=self.doubleF)

        elif self.model_name_front == 'Rec_pre_diff':
            self.input_encoder_lvl1 = self.rec_pre_front(self.in_channel // 2 + 3,
                                                         self.ch_start * self.ch_start_magnitude,
                                                         doubleF=self.doubleF)

        elif self.model_name_front == 'R2_pre_diff':
            self.input_encoder_lvl1 = self.r2_pre_front(self.in_channel // 2 + 3,
                                                        self.ch_start * self.ch_start_magnitude,
                                                        doubleF=self.doubleF)

        elif self.model_name_front == 'RSAB_diff':
            self.input_encoder_lvl1 = self.rsab_front(self.in_channel // 2 + 3, self.ch_start * self.ch_start_magnitude,
                                                      doubleF=self.doubleF)
        elif self.model_name_front == 'ResDrop_diff':
            self.input_encoder_lvl1 = self.resdrop_front(self.in_channel // 2 + 3,
                                                         self.ch_start * self.ch_start_magnitude,
                                                         doubleF=self.doubleF)


        self.down_conv = nn.Conv3d(self.ch_start * ch_start_magnitude, self.ch_start * ch_start_magnitude, 3, stride=2, padding=1,
                                   bias=bias_opt)

        self.resblock_group_lvl1 = self.resblock_seq(self.ch_start * ch_start_magnitude*2, bias_opt=bias_opt)

        self.up_tri = torch.nn.Upsample(scale_factor=2, mode="trilinear", align_corners=True)
        self.up = nn.ConvTranspose3d(self.ch_start * ch_start_magnitude*2, self.ch_start * ch_start_magnitude, 2, stride=2,
                                     padding=0, output_padding=0, bias=bias_opt)

        if self.attn == 'attn':
            self.attention = Attention_block(self.ch_start * self.ch_start_magnitude,
                                             self.ch_start * self.ch_start_magnitude * 2,
                                             self.ch_start * self.ch_start_magnitude * 2, self.attn_batch)

        elif self.attn == 'attn_w_Dil':
            self.attention = Attn_w_Dil(self.ch_start * self.ch_start_magnitude,
                                        self.ch_start * self.ch_start_magnitude * 2,
                                        self.ch_start * self.ch_start_magnitude * 2, self.attn_batch)

        elif self.attn == 'multi_attn':
            self.attention = MultiAttention(self.ch_start * self.ch_start_magnitude,
                                                self.ch_start * self.ch_start_magnitude * 2,
                                                self.ch_start * self.ch_start_magnitude * 2, self.attn_batch,
                                                multiple=self.attn_modi_multiple)

        if self.model_name_back == 'unet_diff':
            self.output_lvl1 = self.outputs(self.ch_start * ch_start_magnitude * self.factor, self.n_classes, kernel_size=3,
                                            stride=1, padding=1, bias=False, doubleB=self.doubleB)
        elif self.model_name_back == 'MSF_diff':
            self.output_lvl1 = self.fire_back(self.ch_start * ch_start_magnitude * self.factor, self.n_classes,
                                              doubleB=self.doubleB)

        elif self.model_name_back == 'MR_diff':
            self.output_lvl1 = self.multiresblock_back(self.ch_start * ch_start_magnitude * self.factor, self.n_classes,
                                                       doubleB=self.doubleB)

        elif self.model_name_back == 'MRD_diff':
            self.output_lvl1 = self.multiresblock_dil_back(self.ch_start * ch_start_magnitude * self.factor, self.n_classes,
                                                           doubleB=self.doubleB)
        elif self.model_name_back == 'Res_diff':
            self.output_lvl1 = self.res_back(self.ch_start * self.ch_start_magnitude * self.factor, self.n_classes,
                                             doubleB=self.doubleB)

        elif self.model_name_back == 'Rec_diff':
            self.output_lvl1 = self.rec_back(self.ch_start * self.ch_start_magnitude * self.factor, self.n_classes,
                                             doubleB=self.doubleB)

        elif self.model_name_back == 'R2_diff':
            self.output_lvl1 = self.r2_back(self.ch_start * self.ch_start_magnitude * self.factor, self.n_classes,
                                            doubleB=self.doubleB)

        elif self.model_name_back == 'Res_pre_diff':
            self.output_lvl1 = self.res_pre_back(self.ch_start * self.ch_start_magnitude * self.factor, self.n_classes,
                                                 doubleB=self.doubleB)

        elif self.model_name_back == 'Rec_pre_diff':
            self.output_lvl1 = self.rec_pre_back(self.ch_start * self.ch_start_magnitude * self.factor, self.n_classes,
                                                 doubleB=self.doubleB)

        elif self.model_name_back == 'R2_pre_diff':
            self.output_lvl1 = self.r2_pre_back(self.ch_start * self.ch_start_magnitude * self.factor, self.n_classes,
                                                doubleB=self.doubleB)

        elif self.model_name_back == 'RSAB_diff':
            self.output_lvl1 = self.rsab_back(self.ch_start * self.ch_start_magnitude * self.factor, self.n_classes,
                                              doubleB=self.doubleB)
        elif self.model_name_back == 'ResDrop_diff':
            self.output_lvl1 = self.resdrop_back(self.ch_start * self.ch_start_magnitude * self.factor, self.n_classes,
                                                 doubleB=self.doubleB)

    def unfreeze_modellvl2(self):
        # unFreeze model_lvl1 weight
        # print("\nunfreeze model_lvl2 parameter")
        for param in self.model_lvl2.parameters():
            param.requires_grad = True

    def resblock_seq(self, in_channels, bias_opt=False):
        layer = nn.Sequential(
            PreActBlock(in_channels, in_channels, bias=bias_opt),
            nn.LeakyReLU(0.2),
            PreActBlock(in_channels, in_channels, bias=bias_opt),
            nn.LeakyReLU(0.2),
            PreActBlock(in_channels, in_channels, bias=bias_opt),
            nn.LeakyReLU(0.2),
            PreActBlock(in_channels, in_channels, bias=bias_opt),
            nn.LeakyReLU(0.2),
            PreActBlock(in_channels, in_channels, bias=bias_opt),
            nn.LeakyReLU(0.2)
        )
        return layer

    def input_feature_extract(self, in_channels, out_channels, kernel_size=3, stride=1, padding=1,
                              bias=False, doubleF=False):
        # print("input_feature_extract in_channels : {}, out_channels : {}".format(in_channels, out_channels))
        # print(f"doubleF : {doubleF}")

        if doubleF:
            layer = nn.Sequential(
                nn.Conv3d(in_channels, out_channels, kernel_size, stride=stride, padding=padding, bias=bias),
                nn.LeakyReLU(0.2),
                nn.Conv3d(out_channels, out_channels, kernel_size, stride=stride, padding=padding, bias=bias)
            )
        else:
            layer = nn.Sequential(
                nn.Conv3d(in_channels, out_channels, kernel_size, stride=stride, padding=padding, bias=bias),
                nn.BatchNorm3d(out_channels),
                nn.ReLU()
            )
        # print(f"layer : {layer}")
        return layer

    def fire_front(self, in_channels, out_channels, doubleF=False):
        # print("fire_front in_channels : {}, out_channels : {}".format(in_channels, out_channels))
        # print(f"doubleF : {doubleF}")
        if doubleF:
            layer = nn.Sequential(
                Multi_Scale_Fire4(in_channels, int(out_channels / (2 * 4)), int(out_channels / (2 * 4))), #2,3,3
                Multi_Scale_Fire4(int(out_channels / (3)), int(out_channels / (2 * 4)), int(out_channels/(4))),#12,3,6
                # Multi_Scale_Fire3(int(out_channels / (2*2)), 3, out_channels/4),
                nn.Softsign()
            )
        else:
            layer = nn.Sequential(
                Multi_Scale_Fire4(in_channels, int(out_channels / 4), int(out_channels/(4)))
            )
        # print(f"layer : {layer}")
        return layer


    def multiresblock_front(self, in_channels, out_channels, doubleF=False):
        # print("multiresblock_front in_channels : {}, out_channels : {}".format(in_channels, out_channels))
        # print(f"doubleF : {doubleF}")
        if doubleF:
            # def __init__(self, num_in_channels, num_filters, alpha=1.67):
            layer = nn.Sequential(
                MultiResblock(in_channels, int(out_channels / 2), 1),
                MultiResblock(int(out_channels / 2), out_channels, 1),
                nn.Softsign()
            )
        else:
            layer = nn.Sequential(
                MultiResblock(in_channels, out_channels, 1)
            )
        # print(f"layer : {layer}")
        return layer

    def multiresblock_dil_front(self, in_channels, out_channels, doubleF=False):
        # print("multiresblock_dil_front in_channels : {}, out_channels : {}".format(in_channels, out_channels))
        # print(f"doubleF : {doubleF}")
        if doubleF:
            layer = nn.Sequential(
                MultiResblock_dil(in_channels, int(out_channels / 2), 1),
                MultiResblock_dil(int(out_channels / 2), out_channels, 1),
                nn.Softsign()
            )
        else:
            layer = nn.Sequential(
                MultiResblock_dil(in_channels, out_channels, 1)
            )
        # print(f"layer : {layer}")
        return layer

    def res_front(self, in_channels, out_channels, doubleF=False):
        if doubleF:
            layer = nn.Sequential(
                ResCNN_block(in_channels, int(out_channels / 2)),
                ResCNN_block(int(out_channels / 2), out_channels),
                nn.Softsign()
            )
        else:
            layer = nn.Sequential(
                ResCNN_block(in_channels, out_channels)
            )
        # print(f"layer : {layer}")
        return layer

    def res_pre_front(self, in_channels, out_channels, doubleF=False):
        if doubleF:
            layer = nn.Sequential(
                ResCNN_pre_block(in_channels, int(out_channels / 2)),
                ResCNN_pre_block(int(out_channels / 2), out_channels),
                nn.Softsign()
            )
        else:
            layer = nn.Sequential(
                ResCNN_pre_block(in_channels, out_channels)
            )
        # print(f"layer : {layer}")
        return layer

    def rec_front(self, in_channels, out_channels, doubleF=False):
        if doubleF:
            layer = nn.Sequential(
                RCNN_block(in_channels, int(out_channels / 2)),
                RCNN_block(int(out_channels / 2), out_channels),
                nn.Softsign()
            )
        else:
            layer = nn.Sequential(
                RCNN_block(in_channels, out_channels, 1)
            )
        # print(f"layer : {layer}")
        return layer

    def rec_pre_front(self, in_channels, out_channels, doubleF=False):
        if doubleF:
            layer = nn.Sequential(
                RCNN_pre_block(in_channels, int(out_channels / 2)),
                RCNN_pre_block(int(out_channels / 2), out_channels),
                nn.Softsign()
            )
        else:
            layer = nn.Sequential(
                RCNN_pre_block(in_channels, out_channels, 1)
            )
        # print(f"layer : {layer}")
        return layer

    def r2_front(self, in_channels, out_channels, doubleF=False):
        if doubleF:
            layer = nn.Sequential(
                RRCNN_block(in_channels, int(out_channels / 2)),
                RRCNN_block(int(out_channels / 2), out_channels),
                nn.Softsign()
            )
        else:
            layer = nn.Sequential(
                RRCNN_block(in_channels, out_channels)
            )
        # print(f"layer : {layer}")
        return layer

    def r2_pre_front(self, in_channels, out_channels, doubleF=False):
        if doubleF:
            layer = nn.Sequential(
                RRCNN_pre_block(in_channels, int(out_channels / 2)),
                RRCNN_pre_block(int(out_channels / 2), out_channels),
                nn.Softsign()
            )
        else:
            layer = nn.Sequential(
                RRCNN_pre_block(in_channels, out_channels)
            )
        # print(f"layer : {layer}")
        return layer

    def rsab_front(self, in_channels, out_channels, doubleF=False):
        if doubleF:
            layer = nn.Sequential(
                Res_drop_block(in_channels, int(out_channels / 2)),
                Res_drop_block(int(out_channels / 2), out_channels),
                # RSAB(out_channels, int(out_channels / 2))
                RSAB(out_channels, out_channels)
            )
        else:
            layer = nn.Sequential(
                Res_drop_block(in_channels, out_channels),
                # RSAB(out_channels, int(out_channels / 2))
                RSAB(out_channels, out_channels)
            )
        # print(f"layer : {layer}")
        return layer

    def resdrop_front(self, in_channels, out_channels, doubleF=False):
        if doubleF:
            layer = nn.Sequential(
                Res_drop_block(in_channels, int(out_channels / 2)),
                Res_drop_block(int(out_channels / 2), out_channels)
            )
        else:
            layer = nn.Sequential(
                Res_drop_block(in_channels, out_channels)
            )
        # print(f"layer : {layer}")
        return layer


    def decoder(self, in_channels, out_channels, kernel_size=2, stride=2, padding=0,
                output_padding=0, bias=True):
        layer = nn.Sequential(
            nn.ConvTranspose3d(in_channels, out_channels, kernel_size, stride=stride,
                               padding=padding, output_padding=output_padding, bias=bias),
            nn.ReLU())
        return layer

    def outputs(self, in_channels, out_channels, kernel_size=3, stride=1, padding=0,
                bias=False, doubleB=False):
        # print("outputs in_channels : {}, out_channels : {}".format(in_channels, out_channels))
        # print(f"doubleB : {doubleB}")
        if doubleB:
            layer = nn.Sequential(
                nn.Conv3d(in_channels, int(in_channels / 2), kernel_size, stride=stride, padding=padding, bias=bias),
                # nn.LeakyReLU(0.2),
                nn.Conv3d(int(in_channels / 2), out_channels, kernel_size, stride=stride, padding=padding, bias=bias),
                nn.Softsign())
        else:
            layer = nn.Sequential(
                nn.Conv3d(in_channels, out_channels, kernel_size, stride=stride, padding=padding, bias=bias),
                nn.BatchNorm3d(out_channels),
                nn.Tanh())
        # print(f"layer : {layer}")
        return layer

    def fire_back(self, in_channels, out_channels, doubleB=False):
        # print("fire_back in_channels : {}, out_channels : {}".format(in_channels, out_channels))
        # print(f"doubleB : {doubleB}")
        if doubleB:
            layer = nn.Sequential(
                Multi_Scale_Fire4(in_channels, int(in_channels / (2 * 4)), int(in_channels / (2 * 4))),
                # nn.LeakyReLU(0.2),
                Multi_Scale_Fire3(int(in_channels / 2), out_channels, 1),
                nn.Softsign()
            )
        else:
            layer = nn.Sequential(
                Multi_Scale_Fire3(in_channels, out_channels, 1)
            )
        # print(f"layer : {layer}")
        return layer

    def multiresblock_dil_back(self, in_channels, out_channels, doubleB=False):
        # print("multiresblock_dil_back in_channels : {}, out_channels : {}".format(in_channels, out_channels))
        # print(f"doubleB : {doubleB}")
        if doubleB:
            layer = nn.Sequential(
                MultiResblock_dil(in_channels, int(in_channels / 2), 1),
                # nn.LeakyReLU(0.2),
                MultiResblock_dil(int(in_channels / 2), out_channels, 1),
                nn.Softsign()
            )
        else:
            layer = nn.Sequential(
                MultiResblock_dil(in_channels, out_channels, 1)
            )
        # print(f"layer : {layer}")
        return layer

    def multiresblock_back(self, in_channels, out_channels, doubleB=False):
        # print("multiresblock_back in_channels : {}, out_channels : {}".format(in_channels, out_channels))
        # print(f"doubleB : {doubleB}")
        if doubleB:
            layer = nn.Sequential(
                MultiResblock(in_channels, int(in_channels / 2), 1),
                # nn.LeakyReLU(0.2),
                MultiResblock(int(in_channels / 2), out_channels, 1),
                nn.Softsign()
            )
        else:
            layer = nn.Sequential(
                MultiResblock(in_channels, out_channels, 1)
            )
        # print(f"layer : {layer}")
        return layer

    def res_back(self, in_channels, out_channels, doubleB=False):
        if doubleB:
            layer = nn.Sequential(
                ResCNN_block(in_channels, int(out_channels / 2)),
                ResCNN_block(int(out_channels / 2), out_channels),
                nn.Softsign()
            )
        else:
            layer = nn.Sequential(
                ResCNN_block(in_channels, out_channels)
            )
        # print(f"layer : {layer}")
        return layer

    def res_pre_back(self, in_channels, out_channels, doubleB=False):
        if doubleB:
            layer = nn.Sequential(
                ResCNN_pre_block(in_channels, int(out_channels / 2)),
                ResCNN_pre_block(int(out_channels / 2), out_channels),
                nn.Softsign()
            )
        else:
            layer = nn.Sequential(
                ResCNN_pre_block(in_channels, out_channels)
            )
        # print(f"layer : {layer}")
        return layer

    def rec_back(self, in_channels, out_channels, doubleB=False):
        if doubleB:
            layer = nn.Sequential(
                RCNN_block(in_channels, int(out_channels / 2)),
                RCNN_block(int(out_channels / 2), out_channels),
                nn.Softsign()
            )
        else:
            layer = nn.Sequential(
                RCNN_block(in_channels, out_channels)
            )
        # print(f"layer : {layer}")
        return layer

    def rec_pre_back(self, in_channels, out_channels, doubleB=False):
        if doubleB:
            layer = nn.Sequential(
                RCNN_pre_block(in_channels, int(out_channels / 2)),
                RCNN_pre_block(int(out_channels / 2), out_channels),
                nn.Softsign()
            )
        else:
            layer = nn.Sequential(
                RCNN_pre_block(in_channels, out_channels)
            )
        # print(f"layer : {layer}")
        return layer

    def r2_back(self, in_channels, out_channels, doubleB=False):
        if doubleB:
            layer = nn.Sequential(
                RRCNN_block(in_channels, int(out_channels / 2)),
                RRCNN_block(int(out_channels / 2), out_channels),
                nn.Softsign()
            )
        else:
            layer = nn.Sequential(
                RRCNN_block(in_channels, out_channels)
            )
        # print(f"layer : {layer}")
        return layer

    def r2_pre_back(self, in_channels, out_channels, doubleB=False):
        if doubleB:
            layer = nn.Sequential(
                RRCNN_pre_block(in_channels, int(out_channels / 2)),
                RRCNN_pre_block(int(out_channels / 2), out_channels),
                nn.Softsign()
            )
        else:
            layer = nn.Sequential(
                RRCNN_pre_block(in_channels, out_channels)
            )
        # print(f"layer : {layer}")
        return layer

    def rsab_back(self, in_channels, out_channels, doubleB=False):
        if doubleB:
            layer = nn.Sequential(
                Res_drop_block(in_channels, int(out_channels / 2)),
                Res_drop_block(int(out_channels / 2), out_channels),
                # RSAB(out_channels, int(out_channels / 2))
                RSAB(out_channels, out_channels)
            )
        else:
            layer = nn.Sequential(
                Res_drop_block(in_channels, out_channels),
                # RSAB(out_channels, int(out_channels / 2))
                RSAB(out_channels, out_channels)
            )
        # print(f"layer : {layer}")
        return layer

    def resdrop_back(self, in_channels, out_channels, doubleB=False):
        if doubleB:
            layer = nn.Sequential(
                Res_drop_block(in_channels, int(out_channels / 2)),
                Res_drop_block(int(out_channels / 2), out_channels)
            )
        else:
            layer = nn.Sequential(
                Res_drop_block(in_channels, out_channels)
            )
        # print(f"layer : {layer}")
        return layer


    def forward(self, x, y):
        # print(f'l3 x.shape : {x.shape}') #torch.Size([1, 1, 144, 160, 192])
        # print(f'l3 y.shape : {y.shape}') #torch.Size([1, 1, 144, 160, 192])
        # output_disp_e0, warpped_inputx_lvl1_out, y_down, compose_field_e0_lvl1v, lvl1_v, e0
        lvl2_disp, _, _,compose_lvl2_v, lvl1_v, lvl2_embedding, f_x_l2, f_y_l2 = self.model_lvl2(x, y)

        # print('\n\n')
        # print(f'l3 lvl2_disp.shape : {lvl2_disp.shape}') #torch.Size([1, 3, 72, 80, 96])
        # print(f'l3 compose_lvl2_v.shape : {compose_lvl2_v.shape}') #torch.Size([1, 3, 72, 80, 96])
        # print(f'l3 lvl1_v.shape : {lvl1_v.shape}') #torch.Size([1, 3, 36, 40, 48])
        # print(f'l3 lvl2_embedding.shape : {lvl2_embedding.shape}') #torch.Size([1, 24, 72, 80, 96])
        # print()
        lvl2_disp_up = self.up_tri(lvl2_disp)
        # print(f'l3 lvl2_disp_up.shape : {lvl2_disp_up.shape}') #torch.Size([1, 3, 144, 160, 192])
        compose_lvl2_v_up = self.up_tri(compose_lvl2_v)
        # print(f'l3 compose_lvl2_v_up.shape : {compose_lvl2_v_up.shape}') #torch.Size([1, 3, 144, 160, 192])
        warpped_x = self.transform(x, lvl2_disp_up.permute(0, 2, 3, 4, 1), self.grid_1)
        # print(f'l3 warpped_x.shape : {warpped_x.shape}') #torch.Size([1, 1, 144, 160, 192])

        cat_input_x = torch.cat((warpped_x, compose_lvl2_v_up), 1)
        # print(f'l3 cat_input_x.shape : {cat_input_x.shape}') #torch.Size([1, 4, 144, 160, 192])
        fea_e0_x = self.input_encoder_lvl1(cat_input_x)
        # print(f'l3 fea_e0_x.shape : {fea_e0_x.shape}')
        f_x = self.avgpool(fea_e0_x)
        # print(f'l3 f_x.shape : {f_x.shape}')
        f_x = f_x.squeeze()
        # print(f'l3 f_x.shape : {f_x.shape}')
        if self.batchsize == 1:
            f_x = f_x.unsqueeze(dim=0)
            # print(f'l3 f_x.shape : {f_x.shape}')
        f_x = self.linear_x(f_x)
        # print(f'l3 f_x.shape : {f_x.shape}')
        f_x = f_x / f_x.norm(dim=-1, keepdim=True)
        # print(f'l3 f_x.shape : {f_x.shape}')


        cat_input_y = torch.cat((y, compose_lvl2_v_up), 1)
        # print(f'l3 cat_input_y.shape : {cat_input_y.shape}')
        fea_e0_y = self.input_encoder_lvl1(cat_input_y)
        # print(f'l3 fea_e0_y.shape : {fea_e0_y.shape}')
        f_y = self.avgpool(fea_e0_y)
        # print(f'l3 f_y.shape : {f_y.shape}')
        f_y = f_y.squeeze()
        # print(f'l3 f_y.shape : {f_y.shape}')
        if self.batchsize == 1:
            f_y = f_y.unsqueeze(dim=0)
            # print(f'l3 f_y.shape : {f_y.shape}')
        f_y = self.linear_y(f_y)
        # print(f'l3 f_y.shape : {f_y.shape}')
        f_y = f_y / f_y.norm(dim=-1, keepdim=True)
        # print(f'l3 f_y.shape : {f_y.shape}')


        e0_x = self.down_conv(fea_e0_x)
        e0_y = self.down_conv(fea_e0_y)
        # print(f'l3 e0_x.shape : {e0_x.shape}')
        # print(f'l3 e0_y.shape : {e0_y.shape}')

        e0_x = e0_x + lvl2_embedding
        e0_y = e0_y + lvl2_embedding
        # print(f'l3 e0_x.shape : {e0_x.shape}')
        # print(f'l3 e0_y.shape : {e0_y.shape}')

        e0 = torch.cat((e0_x, e0_y), 1)
        # print(f'l3 e0.shape : {e0.shape}')
        e0 = self.resblock_group_lvl1(e0)
        # print(f'l3 e0.shape : {e0.shape}')
        e0 = self.up(e0)
        # print(f'l3 e0.shape : {e0.shape}')

        fea_e0 = torch.cat((fea_e0_x, fea_e0_y), 1)
        # print(f'l3 fea_e0.shape : {fea_e0.shape}')
        attn = self.attention(e0, fea_e0)
        # print(f'l3 attn.shape : {attn.shape}')
        # print("attn.shape : {}".format(attn.shape))

        # output_disp_e0_v = self.output_lvl1(torch.cat([e0, fea_e0], dim=1)) * self.range_flow #original
        # output_disp_e0_v = self.output_lvl1(torch.cat([attn, fea_e0], dim=1)) * self.range_flow #this is version 1
        # output_disp_e0_v = self.output_lvl1(torch.cat([attn, e0], dim=1)) * self.range_flow
        if self.concat == 'fea_e0':
            output_disp_e0_v = self.output_lvl1(torch.cat([attn, fea_e0], dim=1)) * self.range_flow
        elif self.concat == 'e0':
            output_disp_e0_v = self.output_lvl1(torch.cat([attn, e0], dim=1)) * self.range_flow
        # print(f'l3 output_disp_e0_v.shape : {output_disp_e0_v.shape}')

        compose_field_e0_lvl2_compose = output_disp_e0_v + compose_lvl2_v_up
        # print(f'l3 compose_field_e0_lvl2_compose.shape : {compose_field_e0_lvl2_compose.shape}')
        output_disp_e0 = self.diff_transform(compose_field_e0_lvl2_compose, self.grid_1)
        # print(f'l3 output_disp_e0.shape : {output_disp_e0.shape}')

        warpped_inputx_lvl1_out = self.transform(x, output_disp_e0.permute(0, 2, 3, 4, 1), self.grid_1)
        # print(f'l3 warpped_inputx_lvl1_out.shape : {warpped_inputx_lvl1_out.shape}')

        if self.is_train is True:
            return output_disp_e0, warpped_inputx_lvl1_out, y, compose_field_e0_lvl2_compose, lvl1_v, compose_lvl2_v, e0, f_x, f_y
        else:
            return output_disp_e0
