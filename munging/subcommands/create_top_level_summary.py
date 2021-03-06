"""
Create the summary file of your choice

Usage:

munge create_summary <Type> $SAVEPATH -o $OUTFILE

"""
import logging
import csv
import sys
import argparse
import collections
from itertools import ifilter
from munging import filters,parsers
from munging.utils import walker

log = logging.getLogger(__name__)

def build_parser(parser):
    parser.add_argument('type', 
                        choices=['pindel','snp','indel','cnv_exon','cnv_gene',
                        'quality','msi_flagged','clin_flagged','hotspot_flagged', 
                        'glt_flagged', 'annotsv', 'amplicon', 'breakdancer',
                        'exon_cov', 'gene_cov'],
                        help='Type of output summary to create')
    parser.add_argument('path',
                        help='Path to analysis files')
    parser.add_argument('pipeline_manifest', type=argparse.FileType('rU'),
                        help='Path to pipeline manifest, used for ordering output')    
    parser.add_argument('-o','--outfile', type = argparse.FileType('w'),
                        default = sys.stdout,
                        help='Name of the output file')
    

def action(args):
    specimens = collections.defaultdict(dict)
    annotation = {}
    prefixes = []
    variant_keys = []
    #Get sort order from pipeline manifest. For TGC, this is alpha numeric. For others it is not. 
    sort_order = [x['barcode_id'] for x in csv.DictReader(args.pipeline_manifest)]
    files = ifilter(filters.any_analysis, walker(args.path))
    if args.type == 'indel':
        parser_type = 'snp'
    elif args.type == 'exon_cov':
        parser_type = 'coveragekit'
        files = list(filter(filters.exon_coverage_analysis, files))
    elif args.type == 'gene_cov':
        parser_type = 'coveragekit'
        files = list(filter(filters.gene_coverage_analysis, files))
    else:
        parser_type = args.type
    analysis_type='_'.join(['parsers.parse',parser_type])
    print "analysis type:",analysis_type
    chosen_parser='{}(files, specimens, annotation, prefixes, variant_keys, sort_order)'.format(analysis_type)
    specimens, annotation, prefixes, fieldnames, variant_keys=eval(chosen_parser)

    writer = csv.DictWriter(args.outfile, fieldnames = fieldnames,  extrasaction = 'ignore', delimiter = '\t')
    writer.writeheader()
    for variant in sorted(specimens.keys()):
        d = {k:v for k,v in zip(variant_keys,variant)}
        d.update({pfx:specimens[variant].get(pfx) for pfx in prefixes})
        d.update(annotation[variant])
        writer.writerow(d)


