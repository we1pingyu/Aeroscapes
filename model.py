import torch
import torch.nn as nn
import torch.nn.functional as F
from segmentation_models_pytorch.encoders import get_encoder
from segmentation_models_pytorch.base import *
import segmentation_models_pytorch as smp
from segmentation_models_pytorch.decoders.unet.decoder import UnetDecoder
from typing import Optional, Union, List


def get_model(name):
    if name == 'unet':
        model = smp.Unet(
            encoder_name="resnet34",
            encoder_weights="imagenet",
            in_channels=3,
            classes=12,
        )
    elif name == 'deeplabv3':
        model = smp.DeepLabV3(
            encoder_name="resnet34",
            encoder_weights="imagenet",
            in_channels=3,
            classes=12,
        )
    elif name == 'deeplabv3plus':
        model = smp.DeepLabV3Plus(
            encoder_name="resnet34",
            encoder_weights="imagenet",
            in_channels=3,
            classes=12,
        )
    elif name == 'mhunet':
        model = DoubleHeadUnet(
            encoder_name="resnet34",
            encoder_weights="imagenet",
            in_channels=3,
            classes=12,
        )
    else:
        raise NotImplementedError("Model {} not found!".format(name))
    return model


class DoubleHeadUnet(smp.Unet):
    def __init__(
        self,
        encoder_name: str = "resnet34",
        encoder_depth: int = 5,
        encoder_weights: Optional[str] = "imagenet",
        decoder_use_batchnorm: bool = True,
        decoder_channels: List[int] = (256, 128, 64, 32, 16),
        decoder_attention_type: Optional[str] = None,
        in_channels: int = 3,
        classes: int = 1,
        activation: Optional[Union[str, callable]] = None,
        aux_params: Optional[dict] = None,
    ):
        super().__init__()

        self.encoder = get_encoder(
            encoder_name,
            in_channels=in_channels,
            depth=encoder_depth,
            weights=encoder_weights,
        )

        self.decoder = UnetDecoder(
            encoder_channels=self.encoder.out_channels,
            decoder_channels=decoder_channels,
            n_blocks=encoder_depth,
            use_batchnorm=decoder_use_batchnorm,
            center=True if encoder_name.startswith("vgg") else False,
            attention_type=decoder_attention_type,
        )

        # self.segmentation_head = SegmentationHead(
        #     in_channels=decoder_channels[-1],
        #     out_channels=classes,
        #     activation=activation,
        #     kernel_size=3,
        # )
        self.thing_segmentation_head = SegmentationHead(
            in_channels=decoder_channels[-1],
            out_channels=12,
            activation=activation,
            kernel_size=3,
        )

        self.stuff_segmentation_head = SegmentationHead(
            in_channels=decoder_channels[-1],
            out_channels=12,
            activation=activation,
            kernel_size=3,
        )

        if aux_params is not None:
            self.classification_head = ClassificationHead(in_channels=self.encoder.out_channels[-1], **aux_params)
        else:
            self.classification_head = None

        self.name = "u-{}".format(encoder_name)
        self.initialize()


    def forward(self, x):
        """Sequentially pass `x` trough model`s encoder, decoder and heads"""

        self.check_input_shape(x)

        features = self.encoder(x)
        decoder_output = self.decoder(*features)

        stuff_masks = self.stuff_segmentation_head(decoder_output)

        thing_masks = self.thing_segmentation_head(decoder_output)

        return stuff_masks,thing_masks
