## pip install pygccxml
import os
import sys
import pickle

# Find out the file location within the sources tree
this_module_dir_path = os.path.abspath(
    os.path.dirname(sys.modules[__name__].__file__))
# Add pygccxml package to Python path
sys.path.append(os.path.join(this_module_dir_path, '..', '..'))


from pygccxml import parser  # nopep8
from pygccxml import declarations  # nopep8
from pygccxml import utils  # nopep8


structStrDict={
        'short unsigned int': 'H',
        'double': 'd',
        'int': 'i',
        'unsigned int':'I',
        'unsigned char':'B',
        'bool':'?',
        'char *':'Q',
        }



# Find out the xml generator (gccxml or castxml)
generator_path, generator_name = utils.find_xml_generator()

# Configure the xml generator
config = parser.xml_generator_configuration_t(
    xml_generator_path=generator_path,
    xml_generator=generator_name,
    compiler="gcc")

# Parsing source file
decls = parser.parse(["Oculus.h"], config)
global_ns = declarations.get_global_namespace(decls)

# Get object that describes unittests namespace
oculus = global_ns.namespace('Oculus')
enums = oculus.enumerations()

enumsDict = {}
classDict = {}
for en in enums:
    packStr = 'I'
    if en.byte_size == 1:
        packStr = 'B'
    elif en.byte_size == 2:
        packStr = 'H'

        
    enumsDict[en.name] = {
            'sizeof':int(en.byte_size),
            'fields': en.get_name2value_dict(),
            'revFields':{v: k for k, v in en.get_name2value_dict().items()},
            'packStr':packStr,
            }

classes = oculus.classes()

for cl in classes:
    cName = cl.name

    print(cl.class_type, cName)
    attDict = {}
    packString = '<'
    for att in  cl.public_members:

        if 'variable' in  att.__str__(): ## gather only variables
            print(att.decl_string)
            try:
                print(att.decl_type.decl_string, att.name, att.decl_type.byte_size)

                if att.decl_type.decl_string.split('::')[-1] in classDict.keys():
                    # flatten all structs attributes for direct parsing
                    attDict.update(classDict[att.decl_type.decl_string.split('::')[-1]]['attributes'])
                    #attDict[att.name]       = classDict[att.decl_type.decl_string.split('::')[-1]]
                    #attDict[att.name].update({'strucType':att.decl_type.decl_string.split('::')[-1]})
                    ps = classDict[att.decl_type.decl_string.split('::')[-1]]['packString'][1:]
                    packString += ps
                elif att.decl_type.decl_string.split('::')[-1] in enumsDict.keys():
                    en = enumsDict[att.decl_type.decl_string.split('::')[-1]]
                    
                    attDict[att.name] = {
                            'sizeof':int(en['sizeof']),
                            'value':att.value,
                            'type':'enum',
                            'packStr':en['packStr']
                            }
                    packString += en['packStr']
                else:
                    if '[' not in att.decl_type.decl_string:
                        ps = structStrDict[att.decl_type.decl_string]
                        tt = 'var'
                        clcSize = att.decl_type.byte_size
                        packString += ps
                        attDict[att.name]={
                                'sizeof':int(clcSize),
                                'value':att.value,
                                'type':tt,
                                'packStr':ps,
                                }
                    else:
                        typeD = att.decl_type.decl_string
                        ps= structStrDict[att.decl_type.decl_string.split('[')[0][:-1]]*int(att.decl_type.decl_string.split('[')[-1][:-1])
                        tt = 'arr_val'
                        packString += ps
                        if att.decl_type.decl_string.split(' ')[1] == 'int':
                            clcSize = att.decl_type.size*4
                            for i in range(att.decl_type.size):
                                attDict['%s_%d'%(att.name, i)]={
                                    'sizeof':4,
                                    'value':att.value,
                                    'type':tt,
                                    'packStr':'I',
                                    }
                        else:
                            print('handle other types...')
                            import ipdb; ipdb.set_trace()
                        
                        
                        
                    

            except:
                print("err")
                import traceback
                traceback.print_exc()
                print('errr...'*3)
                import ipdb; ipdb.set_trace()
    print('--->', packString)
        
    classDict[cName] = {
            'type': cl.class_type,
            'sizeof':int(cl.byte_size),
            'attributes': attDict,
            'packString': packString,
            }

def saveStructs2Pkl():
    with open('oculus_h.pkl', 'wb') as fid:
        data = {'enums':enumsDict, 'structs':classDict}
        pickle.dump(data, fid)

def getBpStruct():
    return {'enums':enumsDict, 'structs':classDict}


if __name__=="__main__":
    saveStructs2Pkl()
