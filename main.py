import json

import pydicom
import os
import zipfile
from sys import argv
import shutil
import json2table
import codecs
import json


def dicom_dataset_tags_extractor(files, include_tags_from_all_files=False):
    original_tags = {}
    for file in files:
        dataset = pydicom.dcmread(file, force=True)
        dataset_dict = dicom_dataset_to_dict(dataset)
        for key_j in dataset_dict.keys():
            original_tags.update(
                {
                    key_j: {dataset_dict[key_j]} if dataset_dict[key_j] not in (None, 'None', ' ', '') else ' _NULL '
                }
            )
    for key_i in original_tags.keys():
        str_value = str(original_tags[key_i])[1:-1]
        original_tags.update(
            {
                key_i: str_value
            }
        )

    return original_tags


def dicom_dataset_to_dict(dicom_header):
    dicom_dict = {}
    # repr(dicom_header)
    for dicom_value in dicom_header.values():
        if dicom_value.tag == (0x7fe0, 0x0010):
            # discard pixel data
            continue
        if type(dicom_value.value) == pydicom.dataset.Dataset:
            dicom_dict[dicom_value.tag] = dicom_dataset_to_dict(dicom_value.value)
        else:
            v = _convert_value(dicom_value.value)
            dicom_dict[dicom_value.tag] = v
    return dicom_dict


def _sanitise_unicode(s):
    return s.replace(u"\u0000", "").strip()


def _convert_value(v):
    t = type(v)
    if t in (list, int, float):
        cv = v
    elif t == str:
        cv = _sanitise_unicode(v)
    elif t == bytes:
        s = v.decode('utf-8', 'replace')

        cv = _sanitise_unicode(s)
    # elif t == pydicom.valuerep.DSfloat:
    #     cv = float(v)
    # elif t == pydicom.valuerep.IS:
    #     cv = int(v)
    # elif t == pydicom.valuerep.PersonName3:
    #     cv = str(v)
    else:
        cv = repr(v)
    return cv


if __name__ == '__main__':
    script, original_file, anonymized_file, table_name = argv

    try:
        shutil.rmtree('original_dicom')
    except:
        pass
    try:
        shutil.rmtree('anonymized_dicom')
    except:
        pass
    try:
        os.remove('html/' + table_name + '.html')
    except:
        pass
    try:
        os.remove('csv/' + table_name + '.csv')
    except:
        pass


    os.mkdir('original_dicom')
    os.mkdir('anonymized_dicom')
    with zipfile.ZipFile(original_file, 'r') as zip_ref:
        zip_ref.extractall('original_dicom')
    with zipfile.ZipFile(anonymized_file, 'r') as zip_ref:
        zip_ref.extractall('anonymized_dicom')

    original_files = [os.path.join(dp, f) for dp, dn, filenames in os.walk('original_dicom') for f in filenames if
                      '._' not in os.path.splitext(f)[0]
                      and '.txt' not in os.path.splitext(f)[1]]

    anonymized_files = [os.path.join(dp, f) for dp, dn, filenames in os.walk('anonymized_dicom') for f in filenames if
                        '._' not in os.path.splitext(f)[0]
                        and '.txt' not in os.path.splitext(f)[1]
                        and '.json' not in os.path.splitext(f)[1]]

    input_dict = dicom_dataset_tags_extractor(original_files)
    output_dict = dicom_dataset_tags_extractor(anonymized_files)

    doc_file = []
    sr_file = []
    ai_files = []
    for file in anonymized_files:
        print(file)
        dataset = pydicom.dcmread(file, force=True)
        if dataset.Modality and dataset.Modality == 'DOC':
            doc_file.append(file)
        elif dataset.Modality and dataset.Modality == 'SR':
            sr_file.append(file)
        else:
            ai_files.append(file)



    doc_dict = dicom_dataset_tags_extractor(doc_file) if doc_file else {'file': 'DOC file not exist'}
    sr_dict = dicom_dataset_tags_extractor(sr_file) if sr_file else {'file': 'SR file not exist'}
    ai_dict = dicom_dataset_tags_extractor(ai_files) if ai_files else {'file': 'AI file not exist'}

    final_dict = {'tags': []}
    i = 0
    for key in set(
            list(input_dict) +
            list(ai_dict) +
            list(doc_dict) +
            list(sr_dict)
    ):
        final_dict['tags'].append({})
        final_dict['tags'][i].update(
            {
                'key': key,
                'input': input_dict[key] if key in input_dict.keys() else '_TAG_NOT_FOUND',
                'ai': ai_dict[key] if key in ai_dict.keys() else '_TAG_NOT_FOUND',
                'doc': doc_dict[key] if key in doc_dict.keys() else '_TAG_NOT_FOUND',
                'sr': sr_dict[key] if key in sr_dict.keys() else '_TAG_NOT_FOUND'
            }
        )

        i += 1

    final_table_html = codecs.open('html/' + table_name + '.html', 'a', 'utf-8-sig')
    build_direction = "LEFT_TO_RIGHT"
    table_attributes = {"style": "width:100%", "border": 1}
    final_table_html.write(json2table.convert(final_dict,
                                              build_direction=build_direction,
                                              table_attributes=table_attributes
                                              )
                           )
    final_table_html.close()

    data = json.load(open('dicom_tags.json'))
    final_table_csv = codecs.open('csv/' + table_name + '.csv', 'a', 'utf-8-sig')
    final_table_csv.write(
        'key,tag_name,input,ai,doc,sr\n')

    for i in range(len(final_dict['tags'])):
        # print(str(final_dict['tags'][i]['key']).replace(', ',','))
        dicom_tag_name = data[str(final_dict['tags'][i]['key']).upper().replace(', ',',')]['Name'] if str(final_dict['tags'][i]['key']).upper().replace(', ',',') in data.keys() else "not_found"
        final_table_csv.write(
            '"' + str(final_dict['tags'][i]['key']).replace('"', '').replace("'", '') + '",' + \
            '"' + dicom_tag_name + '",' + \
            '"' + str(final_dict['tags'][ i]['input']).replace('"', '').replace("'", '') + '",' +\
            '"' + str(final_dict['tags'][i]['ai']).replace('"', '').replace("'", '') + '",' +\
            '"' + str(final_dict['tags'][i]['doc']).replace('"', '').replace("'", '') + '",' +\
            '"' + str(final_dict['tags'][i]['sr']).replace('"', '').replace("'", '') + '"\n'
        )
    final_table_csv.close()
    final_output = set()
    for key in input_dict.keys():
        if key in output_dict.keys():
            if input_dict[key] == output_dict[key]:
                final_output.add('not change: ' + str(key) + str(input_dict[key]))
                # print('not change: ' + str(key) + str(input_dict[key]))
            else:
                final_output.add('change: '+ str(key) + input_dict[key] + ' -> ' + str(output_dict[key]))
                # print('change: '+ str(key) + input_dict[key] + ' -> ' + str(output_dict[key]))
        else:
            final_output.add('remove: ' + str(key) + str(input_dict[key]))
            # print('remove: ' + str(key) + str(input_dict[key]))
    for key in output_dict.keys():
        if key not in input_dict.keys():
            final_output.add('add: ' + str(key) + str(output_dict[key]))
    print(sorted(final_dict))
