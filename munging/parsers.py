"""
Parsers for the top level summary files
pindel, cnv_exon, cnv_gene, snp, msi, quality, clin_flagged
"""
import os
import csv
import sys
import IPython
import copy

from itertools import count, groupby, chain, ifilter 
from operator import itemgetter

from munging import filters
from munging.utils import walker, munge_pfx

"""Each function parses a group of sample files for desired information,
grouping based on the variant_keys list,
some include additional annotation headers,
sample counts, and scores calculated based on counts
"""

def parse_quality(files, specimens, annotation, prefixes, variant_keys):
    """ Parse the sample quality analysis file, from hs_metrics"""
    files = ifilter(filters.quality_analysis, files)
    files=sorted(files)    
    variant_keys = ['MEAN_TARGET_COVERAGE',]
 
    #sort the files so that the output in the workbook is sorted
    for pth in files:      
        pfx = munge_pfx(pth.fname)
        log_pfx=pfx['mini-pfx']
        prefixes.append(log_pfx)
        with open(os.path.join(pth.dir, pth.fname)) as fname:
            reader = csv.DictReader(fname, delimiter='\t')
            for row in reader:
                variant = tuple(k for k in variant_keys)
                specimens[variant][log_pfx] = row['MEAN_TARGET_COVERAGE']
                annotation[variant] = specimens[variant]

    fieldnames = variant_keys + prefixes
    return specimens, annotation, prefixes, fieldnames, variant_keys 

def parse_clin_flagged(files, specimens, annotation, prefixes, variant_keys):
    """Parse the Genotype output, which is the reads of clin_flagged found"""
    files = ifilter(filters.genotype_analysis, files)
    files=sorted(files)    
    variant_keys = ['Position','Ref_Base','Var_Base' ]
    
    #sort the files so that the output in the workbook is sorted
    for pth in files:
        pfx = munge_pfx(pth.fname)
        reads_pfx=pfx['mini-pfx']+'_Reads'
        prefixes.append(reads_pfx)
        with open(os.path.join(pth.dir, pth.fname)) as fname:
            reader = csv.DictReader(fname, delimiter='\t')
            for row in reader:
                variant = tuple(row[k] for k in variant_keys)
                specimens[variant][reads_pfx]=row['Reference_Reads']+'|'+row['Variant_Reads']
                annotation[variant] = row

    annotation_headers = [
        'Clinically_Flagged']
    fieldnames = variant_keys + annotation_headers + prefixes
    return specimens, annotation, prefixes, fieldnames, variant_keys            

def parse_msi(files, control_file, specimens, prefixes, variant_keys):
    """Compare the sample-msi output to the baseline file, report
    Total sites, MSI+ sites and msings score"""
    files = ifilter(filters.msi_file_finder,files) 
    files=sorted(files)    
    
    control_info=csv.DictReader(control_file, delimiter='\t')
    control_info=sorted(control_info, key=itemgetter('Position'))
    control_info=[d for d in control_info]
    
    variant_keys = ['Position',]
    for pth in files:   
        pfx = munge_pfx(pth.fname)
        mini_pfx=pfx['mini-pfx']
        prefixes.append(mini_pfx)
        with open(os.path.join(pth.dir, pth.fname)) as fname:
            reader = csv.DictReader(fname, delimiter='\t')
            sample_msi = sorted(reader, key=itemgetter('Position'))
            for key, group in groupby(sample_msi, key=itemgetter('Position')):
                control_row=[d for d in control_info if d['Position']==key]
                variant = tuple(control_row[0][k] for k in variant_keys)    
                for sample_info in group:
                    if int(sample_info['Avg_read_depth']) >= 30:
                        value = float(control_row[0]['Ave']) + (2 * float(control_row[0]['Std']))
                        if int(sample_info['Number_Peaks']) >= value:
                            new_info = 1
                        else:
                            new_info = 0
                    else:           
                        new_info = None
                    specimens[variant][mini_pfx] = new_info
    #Make copy of dictionary to iterate through
    info=copy.copy(specimens)

    for pfx in prefixes:    
        msi_loci=0
        total_loci=0
        loci=tuple(['passing_loci',])
        msi=tuple(['unstable_loci'],)
        score=tuple(['msing_score'],)
        for entry in info.items():
            if entry[1][pfx] is not None:
                total_loci=total_loci + 1
                msi_loci= msi_loci + entry[1][pfx]
        specimens[loci][pfx]=total_loci
        specimens[msi][pfx]=msi_loci
        specimens[score][pfx]="{0:.4f}".format(float(msi_loci)/total_loci)
    
    fieldnames = variant_keys + list(prefixes) 

    return specimens, prefixes, fieldnames, variant_keys            


def parse_pindel(files, specimens, annotation, prefixes, variant_keys):
    """Parse the pindel analysis file, give total counts of samples with site"""
    #Grab just the pindel files
    files = ifilter(filters.pindel_analysis, files)
    #sort the files so that the output in the workbook is sorted
    files=sorted(files)    
    #List of keys to group samples by
    variant_keys = ['Position', 'Gene']
    #Other annotation to keep 
    annotation_headers = [
        'Gene_Region',
        'Event_Type',
        'Size',
        'Transcripts'
        ]

    #Go through all the files
    for pth in files:
        pfx = munge_pfx(pth.fname)
        #Concatenate the pfx to human readable
        prefixes.append(pfx['mini-pfx'])
        with open(os.path.join(pth.dir, pth.fname)) as fname:
            reader = csv.DictReader(fname, delimiter='\t')
            for row in reader:
                variant = tuple(row[k] for k in variant_keys)
                #Update the specimen dict for this variant, for this pfx, report the Reads found
                specimens[variant][pfx['mini-pfx']] = row['Reads']
                annotation[variant] = row

    #Update the specimen dict for this variant, count samples present
    for key, value in specimens.iteritems():
        specimens[key]['Count']=len(value)

    #Add 'Count' to prefixes for correct dict zipping/printing    
    prefixes.append('Count')
    fieldnames = variant_keys + annotation_headers + prefixes
    return specimens, annotation, prefixes, fieldnames, variant_keys            

def parse_snp(files, specimens, annotation, prefixes, variant_keys):#SNP Specific   
    """Parse the snp output file, give ref|var read counts per sample"""
    files = ifilter(filters.only_analysis, files)
    files = sorted(files)    

    variant_keys = ['Position', 'Ref_Base', 'Var_Base']
    annotation_headers = [
        'Gene',
        'Variant_Type',
        'Transcripts',
        'Clinically_Flagged',
        'Cosmic',
        'Segdup',
        'Polyphen',
        'Sift',
        'Mutation_Taster',
        'Gerp',
        'HiSeq_Freq',
        'HiSeq_Count',
        'MiSeq_Freq',
        'MiSeq_Count',
        '1000g_ALL',
        'EVS_esp6500_ALL',
        '1000g_AMR',
        'EVS_esp6500_AA',
        '1000g_EUR',
        'EVS_esp6500_EU',
        '1000g_ASN',
        '1000g_AFR']

    for pth in files:
        pfx = munge_pfx(pth.fname)
        reads_pfx=pfx['mini-pfx']+'_Ref|Var'
        prefixes.append(reads_pfx)
        with open(os.path.join(pth.dir, pth.fname)) as fname:
            reader = csv.DictReader(fname, delimiter='\t')
            for row in reader:
                variant = tuple(row[k] for k in variant_keys)
                specimens[variant][reads_pfx] = row['Ref_Reads']+'|'+row['Var_Reads']
                annotation[variant] = row
    fieldnames = variant_keys + annotation_headers + prefixes
    return specimens, annotation, prefixes, fieldnames, variant_keys

def parse_cnv_exon(files, specimens, annotation, prefixes, variant_keys):
    """Parse the cnv_exon output, give ave_log_ratio"""
    files = ifilter(filters.cnv_exon_analysis, files)
    files = sorted(files)
    variant_keys = ['Position', 'Gene' ]
    #sort the files so that the output in the workbook is sorted
    for pth in files:
        pfx = munge_pfx(pth.fname)
        log_pfx=pfx['mini-pfx']+'_Log'
        prefixes.append(log_pfx)
        with open(os.path.join(pth.dir, pth.fname)) as fname:
            reader = csv.DictReader(fname, delimiter='\t')
            for row in reader:
                variant = tuple(row[k] for k in variant_keys)
                specimens[variant][log_pfx] = row['Ave_Adjusted_Log_Ratio']
                annotation[variant] = row

    annotation_headers = [
        'Transcripts']
    
    fieldnames = variant_keys + annotation_headers + prefixes
    #print prefixes, fieldnames, variant_keys
    return specimens, annotation, prefixes, fieldnames, variant_keys

def parse_cnv_gene(files, specimens, annotation, prefixes, variant_keys):
    """Parse the cnv_genes output, give ave_log_ratio"""
    files = ifilter(filters.cnv_gene_analysis, files)
    files=sorted(files)
    variant_keys = ['Position', 'Gene' ]
    #sort the files so that the output in the workbook is sorted
    for pth in files:
        pfx = munge_pfx(pth.fname)
        log_pfx=pfx['mini-pfx']+'_Log'
        prefixes.append(log_pfx)
        with open(os.path.join(pth.dir, pth.fname)) as fname:
            reader = csv.DictReader(fname, delimiter='\t')
            for row in reader:
                variant = tuple(row[k] for k in variant_keys)
                specimens[variant][log_pfx] = row['Ave_Adjusted_Log_Ratio']
                annotation[variant] = row

    annotation_headers = [
        'Transcripts']
    fieldnames = variant_keys + annotation_headers + prefixes
    return specimens, annotation, prefixes, fieldnames, variant_keys
    