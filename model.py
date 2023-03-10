import warnings
import torch
from torch import nn

from detector import YoloDetector


class ModuleBuilder:

    def __init__(self, base_cls, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        if self.args is None:
            self.args = []
        elif self.kwargs is None:
            self.kwargs = {}
        self.base_cls = base_cls

    def __setattr__(self, __name, __value):
        if __name in ['args', 'kwargs', 'base_cls', 'build']:
            return super().__setattr__(__name, __value)
        self.kwargs[__name] = __value

    def __getattribute__(self, __name: str):
        if __name in ['args', 'kwargs', 'base_cls', 'build']:
            return super().__getattribute__(__name)
        try:
            index = int(__name)
            return self.args[index]
        except ValueError:
            return self.kwargs[__name]

    def build(self) -> nn.Module:
        return self.base_cls(*self.args, **self.kwargs)


def build_model(arch: dict, disable_bn=False) -> nn.Module:
    model = nn.ModuleList()
    for module_type, args in arch:
        base_cls = nn.Identity
        if module_type == 'conv':
            base_cls = nn.Conv2d
        elif module_type == 'mp':
            base_cls = nn.MaxPool2d
        elif module_type == 'lrelu':
            base_cls = nn.LeakyReLU
        elif module_type == 'softmax':
            base_cls = nn.Softmax
        elif module_type == 'sigmoid':
            base_cls = nn.Sigmoid
        elif module_type == 'bn':
            base_cls = nn.BatchNorm2d
        elif module_type == 'flatten':
            base_cls = nn.Flatten
        elif module_type == 'fc':
            base_cls = nn.Linear
        elif module_type == 'dropout':
            base_cls = nn.Dropout
        elif module_type == 'avgpool':
            base_cls = nn.AvgPool2d
        elif module_type == 'reshape':
            base_cls = YoloReshape
        elif module_type == 'yololoss':
            base_cls = YoloDetector
        elif module_type == 'identity':
            base_cls = nn.Identity
        else:
            warnings.warn("Base class not supported: {}".format(module_type))

        if base_cls == nn.BatchNorm2d and disable_bn:
            continue  # do not insert current layer

        if isinstance(args, (list, tuple)):
            builder = ModuleBuilder(base_cls, *args)
        elif isinstance(args, dict):
            builder = ModuleBuilder(base_cls, None, **args)
        elif args is None:
            builder = ModuleBuilder(base_cls)
        model.append(builder.build())
    return nn.Sequential(*model)


class YoloReshape(torch.nn.Module):

    def __init__(self, *target_shape):
        super(YoloReshape, self).__init__()
        self.target_shape = target_shape

    def forward(self, x):
        return torch.reshape(x, self.target_shape)


class YOLOv1(torch.nn.Module):

    def __init__(self, pretrain_mode=False, disable_bn=True) -> None:
        super().__init__()
        backbone_arch = [
            # Fig.3 Row.1
            ["conv", [3, 64, (7, 7), 2, 3]],
            ["bn", [64]],
            ["lrelu", [0.1]],
            ["mp", [(2, 2), 2]],
            # Fig.3 Row.2
            ["conv", [64, 192, (3, 3), 1, 1]],
            ["bn", [192]],
            ["lrelu", [0.1]],
            ["mp", [(2, 2), 2]],
            # Fig.3 Row.3
            ["conv", [192, 128, (1, 1)]],
            ["bn", [128]],
            ["lrelu", [0.1]],
            ["conv", [128, 256, (3, 3), 1, 1]],
            ["bn", [256]],
            ["lrelu", [0.1]],
            ["conv", [256, 256, (1, 1)]],
            ["bn", [256]],
            ["lrelu", [0.1]],
            ["conv", [256, 512, (3, 3), 1, 1]],
            ["bn", [512]],
            ["lrelu", [0.1]],
            ["mp", [(2, 2), 2]],
            # Fig.3 Row.4
            ["conv", [512, 256, (1, 1)]],
            ["bn", [256]],
            ["lrelu", [0.1]],
            ["conv", [256, 512, (3, 3), 1, 1]],
            ["bn", [512]],
            ["lrelu", [0.1]],
            ["conv", [512, 256, (1, 1)]],
            ["bn", [256]],
            ["lrelu", [0.1]],
            ["conv", [256, 512, (3, 3), 1, 1]],
            ["bn", [512]],
            ["lrelu", [0.1]],
            ["conv", [512, 256, (1, 1)]],
            ["bn", [256]],
            ["lrelu", [0.1]],
            ["conv", [256, 512, (3, 3), 1, 1]],
            ["bn", [512]],
            ["lrelu", [0.1]],
            ["conv", [512, 256, (1, 1)]],
            ["bn", [256]],
            ["lrelu", [0.1]],
            ["conv", [256, 512, (3, 3), 1, 1]],
            ["bn", [512]],
            ["lrelu", [0.1]],
            ["conv", [512, 512, (1, 1)]],
            ["bn", [512]],
            ["lrelu", [0.1]],
            ["conv", [512, 1024, (3, 3), 1, 1]],
            ["bn", [1024]],
            ["lrelu", [0.1]],
            ["mp", [(2, 2), 2]],
            # Fig.3 Row.5.1
            ["conv", [1024, 512, (1, 1)]],
            ["bn", [512]],
            ["lrelu", [0.1]],
            ["conv", [512, 1024, (3, 3), 1, 1]],
            ["bn", [1024]],
            ["lrelu", [0.1]],
            ["conv", [1024, 512, (1, 1)]],
            ["bn", [512]],
            ["lrelu", [0.1]],
            ["conv", [512, 1024, (3, 3), 1, 1]],
            ["bn", [1024]],
            ["lrelu", [0.1]],
        ]
        pretrain_head_arch = [
            ["avgpool", [(7, 7)]],
            ["flatten", [1]],
            ["fc", [1024, 1000]],
        ]
        detection_head_arch = [
            # Fig.3 Row.5.2
            ["conv", [1024, 1024, (1, 1)]],
            ["bn", [1024]],
            ["lrelu", [0.1]],
            ["conv", [1024, 1024, (3, 3), 2, 1]],
            ["bn", [1024]],
            ["lrelu", [0.1]],
            # Fig.3 Row.6
            ["conv", [1024, 1024, (3, 3), 1, 1]],
            ["bn", [1024]],
            ["lrelu", [0.1]],
            ["conv", [1024, 1024, (3, 3), 1, 1]],
            ["bn", [1024]],
            ["lrelu", [0.1]],
            # Fig.3 Row.7
            ["flatten", [1]],
            ["fc", [50176, 4096]],
            ["identity", None],
            ["dropout", 0.5],
            # # Fig.3 Row.8
            ["fc", [4096, 1470]],
            ["reshape", [-1, 30, 7, 7]],
            # Limit range to 0~1, xywhc, classes, all of them.
            ["sigmoid", None]
        ]

        # original paper doesn't have bn implemented on.
        self.backbone = build_model(backbone_arch, disable_bn)
        self.pretrain_head = build_model(pretrain_head_arch, disable_bn)
        self.detection_head = build_model(detection_head_arch, disable_bn)
        self.yolo_detector = YoloDetector(
            cell_size=7,
            box_candidates=2,
            num_classes=20,
        )
        self.pretrain_mode = pretrain_mode

    def forward(self, x, label=None):
        x = self.backbone(x)
        if self.pretrain_mode:
            assert label is None, "Label should not be supplied on pretrain mode"
            x = self.pretrain_head(x)
            return x
        else:
            x = self.detection_head(x)

            if self.training:
                if label is not None:
                    pred, loss = self.yolo_detector(x, label)
                    return pred, loss
                else:
                    warnings.warn('Label not supplied')
                    return x
            else:
                pred = self.yolo_detector(x)
                return pred


if __name__ == '__main__':
    from torchinfo import summary
    summary(
        YOLOv1(pretrain_mode=False),
        input_size=(1, 3, 448, 448),
        verbose=True,
    )
    # summary(
    #     YOLOv1(pretrain_mode=True),
    #     input_size=(1, 3, 224, 224),
    #     verbose=True,
    # )
