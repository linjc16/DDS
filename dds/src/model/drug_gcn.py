import logging
from dataclasses import dataclass, field
from fairseq.dataclass import FairseqDataclass
from fairseq.models import (BaseFairseqModel,
 register_model, register_model_architecture)
import torch
from torch import nn
import torch.nn.functional as F
from omegaconf import II
from fairseq.models.gnn import DeeperGCN

from .heads import BinaryClassMLPv2Head
from .heads_ppi import BinaryClassMLPPPIv2Head
logger = logging.getLogger(__name__)


@dataclass
class GCNConfig(FairseqDataclass):
    dropout: float = field(default=0.1)
    max_positions: int = field(default=512)

    gnn_number_layer: int = field(default=12)
    gnn_dropout: float = field(default=0.1)
    conv_encode_edge: bool = field(default=True)
    gnn_embed_dim: int = field(default=384)
    gnn_aggr: str = field(default='maxminmean')
    gnn_norm: str = field(default='batch')
    gnn_activation_fn: str = field(default='relu')

    classification_head_name: str = field(default='')
    load_checkpoint_heads: bool = field(default=False)

    max_source_positions: int = II("model.max_positions")
    no_token_positional_embeddings: bool = field(default=False)
    pooler_activation_fn: str = field(default='tanh')
    pooler_dropout: float = field(default=0.0)

    n_memory: int = field(default=32)

@register_model("drug_gcn", dataclass=GCNConfig)
class GCNModel(BaseFairseqModel):

    def __init__(self, args, encoder):
        super().__init__()
        self.args = args
        self.encoder = encoder
        self.classification_heads = nn.ModuleDict()
    
    @classmethod
    def build_model(cls, args, task):
        
        base_architecture(args)
        encoder = DeeperGCN(args)
        return cls(args, encoder)

    def forward(self,
                drug_a_seq,
                drug_b_seq,
                drug_a_graph,
                drug_b_graph,
                cell_line,
                features_only=False,
                classification_head_name=None,
                **kwargs):
        
        if classification_head_name is not None:
            features_only = True
        
        enc_a, _ = self.encoder(**drug_a_graph, features_only=features_only, **kwargs)
        enc_b, _ = self.encoder(**drug_b_graph, features_only=features_only, **kwargs)
        
        enc_a = self.get_cls(enc_a)
        enc_b = self.get_cls(enc_b)

        x = self.classification_heads[classification_head_name](enc_a, enc_b, cell_line)

        return x

    def forward_embed(self,
                drug_a_seq,
                drug_b_seq,
                drug_a_graph,
                drug_b_graph,
                cell_line,
                features_only=False,
                classification_head_name=None,
                **kwargs):
        
        if classification_head_name is not None:
            features_only = True
        
        enc_a, _ = self.encoder(**drug_a_graph, features_only=features_only, **kwargs)
        enc_b, _ = self.encoder(**drug_b_graph, features_only=features_only, **kwargs)
        
        enc_a = self.get_cls(enc_a)
        enc_b = self.get_cls(enc_b)

        return enc_a, enc_b

    
    def get_cls(self, x):
        if x is None:
            return 0
        if isinstance(x, torch.Tensor):
            return x[:, -1, :]
        elif isinstance(x, tuple):
            return x[0]
        else:
            raise ValueError()

    def get_targets(self, target, input):
        return target

    def register_classification_head(self, name, num_classes=None, inner_dim=None, **kwargs):
        
        if name in self.classification_heads:
            prev_num_classes = self.classification_heads[name].out_proj.out_features
            prev_inner_dim = self.classification_heads[name].dense.out_features
            if num_classes != prev_num_classes or inner_dim != prev_inner_dim:
                logger.warning('re-registering head "{}" with num_classes {} (prev: {}) '
                               "and inner_dim {} (prev: {})".format(name, num_classes,
                                                                    prev_num_classes, inner_dim,
                                                                    prev_inner_dim))

        if name == 'bclsmlpv2':
            self.classification_heads[name] = BinaryClassMLPv2Head(
                input_dim=getattr(self.encoder, "output_features", self.args.gnn_embed_dim),
                inner_dim=inner_dim or self.args.gnn_embed_dim,
                num_classes=num_classes,
                actionvation_fn=self.args.pooler_activation_fn,
                pooler_dropout=self.args.pooler_dropout,
            )
        elif name == 'bclsmlpppiv2':
            self.classification_heads[name] = BinaryClassMLPPPIv2Head(
                input_dim=getattr(self.encoder, "output_features", self.args.gnn_embed_dim),
                inner_dim=inner_dim or self.args.gnn_embed_dim,
                num_classes=num_classes,
                actionvation_fn=self.args.pooler_activation_fn,
                pooler_dropout=self.args.pooler_dropout,
                n_memory=self.args.n_memory,
            )
        else:
            raise NotImplementedError('No Implemented by DDS')
    
    def max_positions(self):
        return self.args.max_positions

@register_model_architecture("drug_gcn", "drug_gcn_tiny")
def tiny_architecture(args):
    args.gnn_number_layer = getattr(args, "gnn_number_layer", 2)
    args.gnn_embed_dim = getattr(args, "gnn_embed_dim", 384)
    return base_architecture(args)

@register_model_architecture("drug_gcn", "drug_gcn_base")
def base_architecture(args):
    args.gnn_number_layer = getattr(args, "gnn_number_layer", 6)
    args.gnn_embed_dim = getattr(args, "gnn_embed_dim", 384)


@register_model_architecture("drug_gcn", "drug_gcn_large")
def large_architecture(args):
    args.gnn_number_layer = getattr(args, "gnn_number_layer", 12)
    args.gnn_embed_dim = getattr(args, "gnn_embed_dim", 384)
    return base_architecture(args)
