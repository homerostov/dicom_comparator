import pydicom
import os
import zipfile
from sys import argv
import dictdiffer
import shutil

def dicom_dataset_tags_extractor(files):
    original_tags = {}
    for file in files:
        dataset = pydicom.dcmread(file, force=True)
        dataset_dict = dicom_dataset_to_dict(dataset)
        for key_j in dataset_dict.keys():
            if key_j in original_tags.keys():
                if original_tags[key_j] != dataset_dict[key_j]:
                    new_value = original_tags[key_j]
                    new_value.add(dataset_dict[key_j])
                    original_tags.update(
                        {
                            key_j: new_value
                        }
                    )
            else:
                original_tags.update(
                    {
                        key_j: {dataset_dict[key_j]} if dataset_dict[key_j] != None else 'None'
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
        s = v.decode('ascii', 'replace')
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
    try:
        shutil.rmtree('original_dicom')
    except:
        pass
    try:
        shutil.rmtree('anonymized_dicom')
    except:
        pass

    script, original_file, anonymized_file, search_list = argv

    os.mkdir('original_dicom')
    os.mkdir('anonymized_dicom')
    with zipfile.ZipFile(original_file, 'r') as zip_ref:
        zip_ref.extractall('original_dicom')
    with zipfile.ZipFile(anonymized_file, 'r') as zip_ref:
        zip_ref.extractall('anonymized_dicom')

    original_files = [os.path.join(dp, f) for dp, dn, filenames in os.walk('original_dicom') for f in filenames if
             '._' not in os.path.splitext(f)[0]]
    anonymized_files = [os.path.join(dp, f) for dp, dn, filenames in os.walk('anonymized_dicom') for f in filenames if
             '._' not in os.path.splitext(f)[0]]

    a_dict = dicom_dataset_tags_extractor(original_files)
    b_dict = dicom_dataset_tags_extractor(anonymized_files)

    print('\n******* Разница в Исследованиях *******\n')
    for diff in list(dictdiffer.diff(a_dict, b_dict)):
        print(diff)

    if search_list != '':
        print('\n******* Поиск по значениям ('+search_list+') *******\n')
        for key in b_dict.keys():
            if b_dict[key][1:-1] in search_list and b_dict[key][1:-1] != '':
                print(key, b_dict[key])