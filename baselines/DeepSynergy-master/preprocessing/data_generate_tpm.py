from itertools import count
from operator import index
import pandas as pd
from tqdm import tqdm
import pdb
import numpy as np
import os
import torch
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--savedir', type=str)
parser.add_argument('--raw_data_dir', type=str)

args = parser.parse_args()

fold_num = 5

savedir = args.savedir

# savedir = '/data/linjc/dds/baselines/DeepSynergy/data_pt2_new'
# savedir = '/data/linjc/dds/baselines/DeepSynergy/data_leave_cell_new'
# savedir = '/data/linjc/dds/baselines/DeepSynergy/data_leave_comb_new'
os.makedirs(savedir, exist_ok=True)

RAW_DATA_DIR = args.raw_data_dir
# RAW_DATA_DIR = 'baselines/DeepDDs-master/data_ours'
# RAW_DATA_DIR = 'baselines/DeepDDs-master/data_ours_leave_cell'
# RAW_DATA_DIR = 'baselines/DeepDDs-master/data_ours_leave_comb'

df_drug_targets = pd.read_csv('data/drug_target.csv', index_col=0)
df_drug_fpts = pd.read_csv('data/drug_fingerprints.csv', index_col=0)
df_drug_desc = pd.read_csv('data/drug_descriptor.csv', index_col=0)
df_cell_feats = pd.read_csv('data/cell_tpm.csv', index_col=0)


for i in range(fold_num):
    print(f'Generate data for fold{i}.')

    data_name_list = [f'train_fold{i}', f'test_fold{i}', f'valid_fold{i}']
    
    for data_name in data_name_list:

        data = pd.read_csv(os.path.join(RAW_DATA_DIR, f'{data_name}.csv'))
        drug1_feats = []
        drug2_feats = []
        cell_feats = []
        labels = []

        for a, b, cell, y in zip(tqdm(data['drug1_name']), data['drug2_name'], \
            data['cell'], data['label']):

            drug1_feats.append(df_drug_desc.loc[a].tolist() + df_drug_fpts.loc[a].tolist() + df_drug_targets[df_drug_targets['drug_names'] == a].iloc[0, 1:].tolist())
            drug2_feats.append(df_drug_desc.loc[b].tolist() + df_drug_fpts.loc[b].tolist() + df_drug_targets[df_drug_targets['drug_names'] == b].iloc[0, 1:].tolist())
            cell_feats.append(df_cell_feats[df_cell_feats['cell_line_names'] == cell].iloc[0, 1:].tolist())
            labels.append(y)


        drug1_feats = torch.Tensor(drug1_feats)
        drug2_feats = torch.Tensor(drug2_feats)
        cell_feats = torch.Tensor(cell_feats)
        labels = torch.Tensor(labels)

        assert len(drug1_feats) == len(drug2_feats) == len(cell_feats) == len(labels)

        torch.save(drug1_feats, os.path.join(savedir, f'{data_name}_drug1.pt'))
        torch.save(drug2_feats, os.path.join(savedir, f'{data_name}_drug2.pt'))
        torch.save(cell_feats, os.path.join(savedir, f'{data_name}_cell.pt'))
        torch.save(labels, os.path.join(savedir, f'{data_name}_label.pt'))