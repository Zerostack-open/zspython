import __future__
import os
import requests
import json
import re
import pprint
import ast

class ZS_Rest(object):

    def __init__(self,input_dict={}):
        """
        DESC: Set the values for Authentication
        INPUTS: self object
                input_dit - dictionary containing rc variables
                    token_scope - project/domain - default project - Requiered
                    user_region - Required
                    username - Optional
                    password - Optional
                    auth_url - Optional
                    project_name - Optional
                    user_domain_name - Optional
                    project_domain_name - Optional
                    ca_cert_path - Optional
        OUTPUTS: None
        ACCESS: All user accounts
        NOTE: Domain and project scoped tokens will not allow access to the same resources. User region must be specified or
              or an environment variable called USER_REGION must be set or sourced from the RC file.
        """

        if(input_dict['token_scope'] == None or 'token_scope' not in input_dict):
            self.token_scope = 'project'

        elif(str(input_dict['token_scope']).lower() == 'project' or str(input_dict['token_scope']).lower() == 'domain'):
            self.token_scope = input_dict['token_scope']
        else:
            raise Exception("ERROR: Token scope can only be set to project or domain.")

        if('user_region' not in input_dict):
            self.user_region = os.environ.get('USER_REGION')
        elif('user_region' in input_dict):
            self.user_region = input_dict['user_region']
        else:
            raise Exception("ERROR: User region must be specified, check Zerostack Console->Infrastructure Tab, or contact the admin.")

        #fill in the missing input dictionary keys with None
        keys = ['username','password','auth_url','project_name','user_region','user_domain_name','project_domain_name','ca_cert_path']
        for key in keys:
            if(key not in input_dict):
                input_dict[key] = None

        self.auth_username = os.getenv('OS_USERNAME',input_dict['username'])
        self.auth_password = os.getenv('OS_PASSWORD',input_dict['password'])
        self.auth_url = os.getenv('OS_AUTH_URL',input_dict['auth_url'])
        self.project_name = os.getenv('OS_PROJECT_NAME',input_dict['project_name'])
        self.user_domain_name = os.getenv('OS_USER_DOMAIN_NAME',input_dict['user_domain_name'])
        self.project_domain_name=os.getenv('OS_PROJECT_DOMAIN_NAME',input_dict['project_domain_name'])
        self.cacert=os.getenv('OS_CACERT',input_dict['ca_cert_path'])

        if(self.auth_username == None or self.auth_password == None or self.auth_url == None or \
           self.project_name == None or self.user_region == None or self.user_domain_name == None or \
           self.project_domain_name == None or self.cacert == None):
            print "Export the Zerostack RC file, or explicitly define authentication variables"

        #Derive the zerostack url from the auth url, unless specified, will not work with Zerostack glance API endpoint
        self.zs_url = self.auth_url[:-12]

    def run_rest(self,input_dict):
        """
        DESC: Run the rest calls
        INPUTS: self object
                input_dict - dictionary containing rest call information
                    body - Optional - Default None
                    headers - Optional - Default {"content-type":"application/json"}
                    verify - Optional - Default False
                    url - required
                    verb - Rest Operation - GET,PUT,POST,DELETE,PATCH,HEAD
        OUTPUTS: None
        ACCESS: All user accounts
        NOTE: Domain and project scoped tokens will not allow access to the same resources. User region must be specified or
              or an environment variable called USER_REGION must be set or sourced from the RC file.
        """
        #initialize a regex to check URL
        regex = re.compile(
            r'^(?:http|ftp)s?://'
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'
            r'localhost|'
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
            r'(?::\d+)?'
            r'(?:/?|[/?]\S+)$', re.IGNORECASE
            )

        if('body' not in input_dict):
            self.body = None
        else:
            #try:
            self.body = input_dict['body']
            #except ValueError as v:
            #self.body = input_dict['body']

        if('headers' not in input_dict):
            self.headers = {"content-type":"application/json"}
        else:
            self.headers = input_dict['headers']

        if('verify' not in input_dict):
            self.verify = True
        else:
            self.verify = input_dict['verify']

        if('verb' not in input_dict):
            raise Exception("ERROR: No REST verb specified.")

        ops = ['POST','DELETE','PUT','GET','PATCH','HEAD']
        if(str(input_dict['verb']).upper() not in ops):
            raise Exception("ERROR: REST verb not valid.")

        if('url' not in input_dict):
            raise Exception("ERROR: No API URL endpoint url specified.")

        if(re.match(regex, str(input_dict['url'])) is not None):
            self.url = str(input_dict['url'])
        else:
            raise Exception("ERROR: API URL is mal formed.")

        print self.url
        print type(self.url)
        print self.body
        print type(self.body)
        r = requests.request(str(input_dict['verb']).upper(), verify=self.verify, headers=self.headers, url=self.url, data=self.body)
        out = r.raise_for_status()
        if(out != None):
            raise Exception(out)

        return r

class Zerostack(object):

    def __init__(self,input_dict):
        """
        DESC: Set the values for Authentication
        INPUTS: self object
                input_dict  - token_scope - project/domain - default project - Requiered
                            - user_region - Required
                            - username - Optional
                            - password - Optional
                            - auth_url - Optional
                            - project_name - Optional
                            - user_domain_name - Optional
                            - project_domain_name - Optional
                            - ca_cert_path - Optional
        OUTPUTS: None
        ACCESS: All user accounts
        NOTE: Domain and project scoped tokens will not allow access to the same resources
        """
        self.rest = ZS_Rest(input_dict)
        self.raw_token_body = None

    def authenticate(self):
        """
        DESC: Use the set values to authenticate against Zerostack.
        INPUTS: self object
        OUTPUTS: r_dict - zs_token
                        - zs_token_scope
        ACCESS: All user accounts
        NOTE: Domain and project scoped tokens will not allow access to the same resources
        """
        body = None

        if(self.rest.token_scope == 'project'):
            body = '{"auth":{"identity":{"methods":["password"],"password":{"user":{"name":"%s","domain":{"name":"%s"},"password":"%s"}}},"scope":{"project":{"name":"%s","domain":{"name":"%s"}}}}}' \
                    %(self.rest.auth_username,self.rest.project_domain_name,self.rest.auth_password,self.rest.project_name,self.rest.project_domain_name)
        else:
            body = '{"auth":{"identity":{"methods":["password"],"password":{"user":{"domain":{"name":"%s"},"name":"%s","password":"%s"}}},"scope":{"domain":{"name":"%s"}}}}' \
                   %(self.rest.project_domain_name,self.rest.auth_username,self.rest.auth_password,self.rest.project_domain_name)

        headers={"content-type":"application/json"}

        self.raw_token_body = self.rest.run_rest({'body':body,'headers':headers,'verify':True,'url':self.rest.auth_url+'/auth/tokens','verb':'POST'})

        return {'zs_token_scope':self.rest.token_scope,'zs_token':self.raw_token_body.headers.get('X-Subject-Token')}

    def logout(self,zs_token=None):
        """
        DESC: Set the values for Authentication
        INPUTS: self object
                zs_token
        OUTPUTS: r_dict - status
        ACCESS: All user accounts
        NOTE: Domain and project scoped tokens will not allow access to the same resources
        """
        try:
            logout = requests.delete(self.auth_url,verify = False,data = body,headers={"content-type":"application/json"})
        except requests.exceptions.HTTPError as e:
            raise(e)

        return {'status':logout.status_code}

    def get_raw_zstoken_contents(self):
        """
        DESC: Get the full output of the token generation. This will include user info, endpoints, and domains.
        INPUTS: self object
        OUTPUTS: raw token object that needs to be processed
        ACCESS: All user accounts
        NOTE: This is an object which will be composed of lists of dictionaries.
        """
        return self.raw_token_body.text

    def get_zsproject(self):
        """
        DESC: Get the project ID and project Name.
        INPUTS: self object
        OUTPUTS: r_dict - zs_project_name
                        - zs_project_id
        ACCESS: All user accounts
        NOTE: Will return None if a domain token is used.
        """
        raw_contents = json.loads(get_raw_zstoken_contents())

        if(self.rest.token_scope == 'project'):
            self.project_id = raw_contents['token']['project']['id']
            self.project_name = raw_contents['token']['project']['name']
        else:
            self.project_id = None
            self.project_name = None

        return {'zs_project_name':self.project_name,'zs_project_id':self.project_id}

    def get_zsproject_id(self):
        """
        DESC: Return the project ID.
        INPUTS: self object
        OUTPUTS: zs_project_id
        ACCESS: All user accounts
        NOTE: None
        """
        if(self.rest.token_scope == 'domain'):
            return 'WARN: Domain scope token can not return project ID.'
        raw = self.get_zsproject()

        return {'zs_project_id':raw['project_id']}

    def get_zs_bu(self):
        """
        DESC: Get the bu name and the bu id attached to the token.
        INPUTS: self object
        OUTPUTS: r_dict - zs_bu_name
                        - zs_bu_id
        ACCESS: All user accounts
        NOTE: None
        """
        raw_contents = json.loads(self.get_raw_zstoken_contents())

        if(self.rest.token_scope == 'project'):
            self.domain_id = raw_contents['token']['project']['domain']['id']
            self.domain_name = raw_contents['token']['project']['domain']['name']
        else:
            self.domain_id = raw_contents['token']['user']['domain']['id']
            self.domain_name = raw_contents['token']['user']['domain']['name']

        return {'zs_bu_name':self.domain_name,'zs_bu_id':self.domain_id}

    def get_zsbu_id(self):
        """
        DESC: Return the bu ID of the token.
        INPUTS: self object
        OUTPUTS: zs_bu_id
        ACCESS: All user accounts
        NOTE: None
        """
        raw = self.get_zs_bu()
        return {'zs_bu_id':raw['zs_bu_id']}

    def get_zs_region_id(self):
        """
        DESC: Return the region ID.
        INPUTS: self object
        OUTPUTS: zs_region_id
        ACCESS: All user accounts
        NOTE: None
        """
        split = str(self.rest.auth_url).split('/')
        #region id is element 6
        return {'zs_region_id':split[6]}

    def get_raw_zscatalog(self):
        """
        DESC: Get the raw service catalog output.
        INPUTS: self object
        OUTPUTS: Raw catalog list data structure.
        ACCESS: All user accounts
        NOTE: Output is a list of dictionaries.
        """
        raw_contents = json.loads(self.get_raw_zstoken_contents())
        return raw_contents['token']['catalog']

    def get_zstoken_owner(self):
        """
        DESC: Get the user ID and Roles of the Token Owner
        INPUTS: self object
        OUTPUTS: r_dict - user_name
                        - user_id
                        - roles list - role_name
                                     - role_id
        ACCESS: All user accounts
        NOTE: None
        """
        raw_contents = json.loads(self.get_raw_zstoken_contents())

        if(self.rest.token_scope == 'project'):
            self.user_id = raw_contents['token']['user']['id']
            self.user_name = raw_contents['token']['user']['name']
            self.roles = raw_contents['token']['roles']
        else:
            self.user_id = raw_contents['token']['user']['id']
            self.user_name = raw_contents['token']['user']['name']
            self.roles = raw_contents['token']['roles']

        return {'user_id':self.user_id,'user_name':self.user_name,'roles':self.roles}

    def list_zs_services(self):
        """
        DESC: Return a list of cloud service endpoints types in the Zerostack cloud.
        INPUTS: self object
        OUTPUTS: list of dictionaries
                 dict - zs_endpoint_name
                      - zs_endpoint_id
                      - zs_endpoint_type
        ACCESS: All user accounts
        NOTE: None
        """
        raw_endpoints = self.get_raw_zscatalog()
        r_list = []
        for endpoint in raw_endpoints:
            r_list.append({'zs_endpoint_name':endpoint['name'],'zs_endpoint_id':endpoint['id'],'zs_endpoint_type':endpoint['type']})
        return r_list

    def get_zs_endpoint(self,endpoint_id=None):
        """
        DESC: Get detailed endpoint information
        INPUTS: self object
                endpoint_id
        OUTPUTS:
        ACCESS: All user accounts
        NOTE: None
        """
        if(endpoint_id == None):
            raise "Error: No endpoint ID given."
        catalog = self.get_raw_zscatalog()
        return (item for item in catalog if item["id"] == endpoint_id).next()

##############Business Unit CRUD###########################
    def create_zsbusiness_unit(self,input_dict):
        """
        DESC: Create a new business unit in zerostack
        INPUTS: self object
                input_dict - bu_name - Req - name of BU
                           - bu_description - Req - Description of a BU
        OUTPUTS: r_dict - zs_bu_id
                        - zs_bu_name
                        - zs_bu_desc
        ACCESS: Cloud admins
        NOTE: MUST have valid cloud admin rc file and zs_token in order to perform this operation. Check OS_PROJECT_DOMAIN_NAME=admin.local
        """
        if('bu_name' not in input_dict or 'bu_description' not in input_dict):
            raise Exception("Domain creation values values not given.")

        if('ldapSet' not in input_dict):
            input_dict['ldapSet'] = 'false'

        ldap_vals = ['true','false']
        if(str(input_dict['ldapSet']).lower() not in ldap_vals):
            raise Exception("Domain creation values values not given.")

        body = '{"domain":{"name":"%s","description":"%s","ldapSet":"%s"}}'%(input_dict['bu_name'],input_dict['bu_description'],input_dict['ldapSet'])
        headers = {"content-type":"application/json;charset=UTF-8",
                   "Origin":"https://console.zerostack.com",
                   "X-Auth-Token":self.raw_token_body.headers.get('X-Subject-Token')}

        try:
            raw = self.rest.run_rest({'body':body,'headers':headers,'verify':True,'url':self.rest.auth_url+'/domains','verb':'POST'})
            out = json.loads(raw.text)
            return {'zs_bu_id':out['domain']['id'],'zs_bu_name':out['domain']['name'],'zs_bu_desc':out['domain']['description']}
        except Exception as e:
            return e

    def list_zsbusiness_units(self):
        """
        DESC: List the business units.
        INPUTS: self object
        OUTPUTS: array of dictionaries  - zs_bu_id - Business unit ID
                                        - zs_bu_name - Name of the business unit
                                        - zs_bu_desc - Business unit description is any
        ACCESS: cloud admin
        NOTE:
        """
        headers = {"content-type":"application/json",
                   "X-Auth-Token":self.raw_token_body.headers.get('X-Subject-Token')}
        out_array = []

        try:
            raw_bu = self.rest.run_rest({'body':None,
                                        'headers':headers,
                                        'verify':True,
                                        'url':self.rest.auth_url+'/domains',
                                        'verb':'GET'})
            out = json.loads(raw_bu.text)
            for o in out['domains']:
                out_array.append({'zs_bu_id':o['id'],'zs_bu_name':o['name'],'zs_bu_desc':o['description']})
            return out_array
        except Exception as e:
            return e

    def get_zsbusiness_unit(self,bu_id=None):
        """
        DESC: Get detailed BU information.
        INPUTS: self object
                bu_id - Zerostack business unit
        OUTPUTS: out_dict - zs_bu_id - Business unit ID
                          - zs_bu_name - Name of the business unit
                          - zs_bu_desc - Business unit description is any
        ACCESS: cloud admins
        NOTE:
        #return self.zsauth.authenticate()
        """
        #print self.zsauth.list_zs_services()
        headers = {"content-type":"application/json",
                   "X-Auth-Token":self.raw_token_body.headers.get('X-Subject-Token')}

        #bu_project =

        try:
            raw_bu = self.rest.run_rest({'body':None,
                                        'headers':headers,
                                        'verify':True,
                                        'url':self.rest.auth_url+'/domains/'+bu_id,
                                        'verb':'GET'})
            out = json.loads(raw_bu.text)
            return {'zs_bu_id':out['domain']['id'],'zs_bu_name':out['domain']['name'],'zs_bu_desc':out['domain']['description']}
        except Exception as e:
            return e

    def delete_zsbusiness_unit(self,bu_id=None):
        """
        DESC: Delete a business unit
        INPUTS: self object
                bu_id
        OUTPUTS: out_dict - zs_bu_id
                          - zs_bu_name
                          - zs_bu_deleted
        ACCESS: Cloud admins
        NOTE: None
        """
        body = '{"domain":{"enabled":false}}'
        headers = {"content-type":"application/json;charset=UTF-8",
                   "Origin":"https://console.zerostack.com",
                   "X-Auth-Token":self.raw_token_body.headers.get('X-Subject-Token')}

        try:
            update = self.rest.run_rest({'body':body,
                                            'headers':headers,
                                            'verify':True,
                                            'url':self.rest.auth_url+'/domains/'+bu_id,
                                            'verb':'PATCH'})
            zsbu_up = json.loads(update.text)
        except Exception as e:
            return e

        try:
            raw_bu = self.rest.run_rest({'body':None,
                                        'headers':headers,
                                        'verify':True,
                                        'url':self.rest.auth_url+'/domains/'+bu_id,
                                        'verb':'DELETE'})
        except Exception as e:
            return e

        return {'zs_bu_id':zsbu_up['domain']['id'],'zs_bu_name':zsbu_up['domain']['name'],'zs_bu_deleted':True}

#######BU Projects CRUD################

    def create_zsproject(self,input_dict):
        """
        DESC: Create a new project in the Zerostack business unit.
        INPUTS: self object
                description - op
                zs_bu_id - req
                project_name - req
                finite_duration - true/false - op
                duration - if finite duration specified, default 1 week - op
                quota_Level - small,medium,large,custom - default medium
                custom_quota - op - json formated string, see NOTE
        OUTPUTS: zs_proj_id
        ACCESS: Cloud admin
                BU admin - domain token needed.
        NOTE: '{ \
                 "compute_quota":{"cores":INT,"floating_ips":INT,"injected_file_content_bytes":-1,"injected_file_path_bytes":-1,"injected_files":-1,"instances":INT,"key_pairs":-1,"metadata_items":-1,"ram":INT}, \
                 "storage_quota":{"backup_gigabytes":-1,"backups":-1,"snapshots":INT,"volumes":INT,"gigabytes":INT},\
                 "network_quota":{"subnet":-1,"router":INT,"port":-1,"network":INT,"floatingip":INT,"vip":-1,"pool":-1} \
                }'
        """
        region_id = self.get_zs_region_id()
        url = 'https://console.zerostack.com/v2/clusters/%s/projects'%(region_id['zs_region_id'])

        input_dict['finite_duration'] = 'false'
        #if('finite_duration' not in input_dict):
        #    input_dict['finite_duration'] = 'false'

        #if(str(input_dict['finite_duration']).lower() == 'true'):
            #comeing soon
        #    pass

        #this is the defualt
        quota = '{"compute_quota":{"cores":64,"floating_ips":32,"injected_file_content_bytes":-1,"injected_file_path_bytes":-1,"injected_files":-1,"instances":32,"key_pairs":-1,"metadata_items":-1,"ram":131072},"storage_quota":{"backup_gigabytes":-1,"backups":-1,"snapshots":320,"volumes":320,"gigabytes":1280},"network_quota":{"subnet":-1,"router":20,"port":-1,"network":32,"floatingip":32,"vip":-1,"pool":-1}}'
        template = 'Medium'
        custom_temp = 'true'

        if('quota_level' in input_dict and input_dict['quota_level'] == 'small'):
            quota = '''{"compute_quota":{"cores":16,"floating_ips":8,"injected_file_content_bytes":-1,"injected_file_path_bytes":-1,"injected_files":-1,"instances":8,"key_pairs":-1,"metadata_items":-1,"ram":32768},"storage_quota":{"backup_gigabytes":-1,"backups":-1,"snapshots":80,"volumes":80,"gigabytes":320},"network_quota":{"subnet":-1,"router":10,"port":-1,"network":10,"floatingip":8,"vip":-1,"pool":-1}}'''
            template = 'Small'
            custom_temp = 'true'

        elif('quota_level' in input_dict and input_dict['quota_level'] == 'medium'):
            quota = '''{"compute_quota":{"cores":64,"floating_ips":32,"injected_file_content_bytes":-1,"injected_file_path_bytes":-1,"injected_files":-1,"instances":32,"key_pairs":-1,"metadata_items":-1,"ram":131072},"storage_quota":{"backup_gigabytes":-1,"backups":-1,"snapshots":320,"volumes":320,"gigabytes":1280},"network_quota":{"subnet":-1,"router":20,"port":-1,"network":32,"floatingip":32,"vip":-1,"pool":-1}}'''
            template = 'Medium'
            custom_temp = 'true'

        elif('quota_level' in input_dict and input_dict['quota_level'] == 'large'):
            quota = '{"compute_quota":{"cores":128,"floating_ips":64,"injected_file_content_bytes":-1,"injected_file_path_bytes":-1,"injected_files":-1,"instances":64,"key_pairs":-1,"metadata_items":-1,"ram":262144},"storage_quota":{"backup_gigabytes":-1,"backups":-1,"snapshots":640,"volumes":640,"gigabytes":25600},"network_quota":{"subnet":-1,"router":20,"port":-1,"network":64,"floatingip":64,"vip":-1,"pool":-1}}'
            template = 'Large'
            custom_temp = 'true'

        elif('quota_level' in input_dict and input_dict['quota_level'] == 'custom'):
            quota = input_dict['custome_quota']
            template = 'Custom'
            custom_temp = 'true'

        body = '{"description":"%s","domain_id":"%s","name":"%s","finite_duration":"%s","metadata":{"templateId":"%s","custom_template":"%s"},"quota":"%s"'%(input_dict['description'],
                                                                                                                                                             input_dict['zs_bu_id'],
                                                                                                                                                             input_dict['project_name'],
                                                                                                                                                             str(input_dict['finite_duration']).lower(),
                                                                                                                                                             template,custom_temp,quota)
        headers = {"content-type":"application/json;charset=UTF-8",
                   "Origin":"https://console.zerostack.com",
                   "X-Auth-Token":self.raw_token_body.headers.get('X-Subject-Token')}
        #try:
        raw_bu = self.rest.run_rest({'body':body,
                                    'headers':headers,
                                    'verify':True,
                                    'url':url,
                                    'verb':'POST'})
        out = json.loads(raw_bu.text)
        #except Exception as e:
        #    return e

        return out


    def get_zsproject(self,project_id=None):
        """
        DESC: Get project details
        INPUTS: self object
                zs_token - generated from ZS_Auth
        OUTPUTS: None
        ACCESS: Cloud admin
                BU admin - domain token needed.
        NOTE: None
        """
        pass

    def list_zsprojects(self,bu_id=None):
        """
        DESC: List the projects in the BU.
        INPUTS: self object
                bu_id
        OUTPUTS: dict of list - zs_projects
        ACCESS: Cloud admin
                BU admin - domain token needed.
        NOTE: Domain scope token must be used
        """
        headers = {"content-type":"application/json;charset=UTF-8",
                   "Origin":"https://console.zerostack.com",
                   "X-Auth-Token":self.raw_token_body.headers.get('X-Subject-Token')}
        if(bu_id == None):
            x = self.get_zsbu_id()
            bu_id = x['zs_bu_id']
        try:
            raw_bu = self.rest.run_rest({'body':None,
                                        'headers':headers,
                                        'verify':True,
                                        'url':self.rest.auth_url+'/projects/?domain_id='+bu_id,
                                        'verb':'GET'})
            out = json.loads(raw_bu.text)
        except Exception as e:
            return e

        return {'zs_projects':out['projects']}

    def delete_zsproject(self,project_id=None):
        """
        DESC: Delete a project.
        INPUTS: self object
                project_id - Required
        OUTPUTS:
        ACCESS: Cloud admin
                BU admin - domain token needed.
        NOTE: need a valid domain token
        """
        return "Not implemented."

    def create_user(self,input_dict):
        """
        DESC: Add a new user to a project
        INPUTS: self object
                input_dict - username - req
                           - useremail - req
                           - password - req
                           - role - admin/member - req
                           - zs_bu_id - op - default admin bu
        OUTPUTS: zs_userid
        ACCESS: Only Cloud and BU admins
        NOTE: None
        """
        if(self.rest.token_scope == 'project'):
            return 'Can not create user with project scope token.'

        bu = []
        zs_bu_id = None

        #get the BU ids
        for zsbu in self.list_zsbusiness_units():
            bu.append(zsbu['zs_bu_id'].encode('latin-1'))

        if('zs_bu_id' not in input_dict):
            zs_bu_id = self.get_zsbu_id()
        elif(input_dict['zs_bu_id'] in bu):
            zs_bu_id = input_dict['zs_bu_id']

        body = '{"user":{"email":"%s",\
               "enabled":true,\
               "name":"%s",\
               "domain_id":"%s",\
               "password":"%s"}}'%(input_dict['useremail'],input_dict['username'],zs_bu_id,input_dict['password'])

        headers = {"content-type":"application/json;charset=UTF-8",
                   "Origin":"https://console.zerostack.com",
                   "X-Auth-Token":self.raw_token_body.headers.get('X-Subject-Token')}

        #get the desired role id
        try:
            raw_roles = self.rest.run_rest({'body':None,
                                        'headers':headers,
                                        'verify':True,
                                        'url':self.rest.auth_url+'/roles',
                                        'verb':'GET'})
            roleout = json.loads(raw_roles.text.encode('latin-1'))
        except Exception as e:
            return e

        role_id = None
        try:
            for role in roleout['roles']:
                if(role['name'] == '_member_' and str(input_dict['role']).lower() == 'member'):
                    role_id = role['id']
                elif(role['name'] == 'admin' and str(input_dict['role']).lower() == 'admin'):
                    role_id = role['id']
        except Exception as e:
            return e

        #create the new user
        try:
            raw_user = self.rest.run_rest({'body':body,
                                        'headers':headers,
                                        'verify':True,
                                        'url':self.rest.auth_url+'/users',
                                        'verb':'POST'})
            out = json.loads(raw_user.text)
        except Exception as e:
            return e

        try:
            raw_role = self.rest.run_rest({'body':None,
                                        'headers':headers,
                                        'verify':True,
                                        'url':self.rest.auth_url+'/domains/'+zs_bu_id+'/users/'+out['user']['id']+'/roles/'+role_id,
                                        'verb':'PUT'})
        except Exception as e:
            return e

        return {'zs_user_id':out['user']['id'],'zs_user_name':out['user']['name']}

    def delete_user(self):
        """
        DESC: Set the login token.
        INPUTS: self object
                zs_token - generated from ZS_Auth
        OUTPUTS: None
        ACCESS: All user accounts
        NOTE: None
        """
        return "Not implemented"

    def list_users(self):
        """
        DESC: Set the login token.
        INPUTS: self object
                zs_token - generated from ZS_Auth
        OUTPUTS: None
        ACCESS: All user accounts
        NOTE: None
        """
        return "Not implemented"


    def get_user(self):
        """
        DESC: Set the login token.
        INPUTS: self object
                zs_token - generated from ZS_Auth
        OUTPUTS: None
        ACCESS: All user accounts
        NOTE: None
        """
        return "Not implemented"

    def apply_user_role(self):
        """
        DESC: Apply a role to a user.
        INPUTS: self object
        OUTPUTS: None
        ACCESS: Cloud Admins, BU Admins
        NOTE: None
        """
        return "Not implemented"

    def list_user_roles(self):
        pass


    def list_apps():
        pass
    def get_app():
        pass
    def deploy_app():
        pass
    def upload_app_template():
        pass
    def delete_app():
        pass

class ZS_Compute(object):
    def __init__(self, zs_token=None):
        """
        DESC: Set the login token.
        INPUTS: self object
                zs_token - generated from ZS_Auth
        OUTPUTS: None
        ACCESS: All user accounts
        NOTE: None
        """
        if(zs_token == None):
            raise "ERROR: zs_token is blank, check your token."

        self.zs_token = zs_token

        self.rest = ZS_Rest()

    def get_zs_instance(self,instance_id=None):
        """
        DESC: Set the login token.
        INPUTS: self object
                zs_token - generated from ZS_Auth
        OUTPUTS: None
        ACCESS: All user accounts
        NOTE: None
        """
        self.rest.run_rest()
        pass

    def list_zs_instances(self):
        """
        DESC: List the instances in the project.
        INPUTS: self object
                zs_token - generated from ZS_Auth
        OUTPUTS: r_dict - instance_name
                        - instance_id
        ACCESS: All user accounts
        NOTE: You must have a token in the project context in order to list the instances.
        """
        #https://console.ZeroStack.com/os/fb08e841-c5bf-472e-b5be-3bebb64b3470/regions/0a3b7f9e-617e-485c-88ce-c8c37775efe4/nova/v2/9a7cd63fa36642318a5de4c3dad01ab8/servers/detail
        try:
            self.raw_instance_list = requests.post(self.auth_url,verify = False,data = body,headers={"content-type":"application/json"})
        except requests.exceptions.HTTPError as e:
            raise(e)

        return {'zs_token_scope':self.token_scope,'zs_token':self.raw_token_body.headers.get('X-Subject-Token')}


    def create_zs_instance(self,input_dict):
        """
        DESC: Set the login token.
        INPUTS: self object
                zs_token - generated from ZS_Auth
        OUTPUTS: None
        ACCESS: All user accounts
        NOTE: None
        """
        pass

    def delete_zs_instance(self,instance_id=None):
        """
        DESC: Set the login token.
        INPUTS: self object
                zs_token - generated from ZS_Auth
        OUTPUTS: None
        ACCESS: All user accounts
        NOTE: None
        """
        pass


#########Networking######################
    def connect_zs_network(self,input_dict):
        """
        DESC: Set the login token.
        INPUTS: self object
                zs_token - generated from ZS_Auth
        OUTPUTS: None
        ACCESS: All user accounts
        NOTE: None
        """
        pass

    def disconnect_zs_network(self,instance_id=None):
        """
        DESC: Set the login token.
        INPUTS: self object
                zs_token - generated from ZS_Auth
        OUTPUTS: None
        ACCESS: All user accounts
        NOTE: None
        """
        pass



    #def connect_zs_volume(self,input_dict):
    #    """
    #    DESC: Set the login token.
    #    INPUTS: self object
    #            zs_token - generated from ZS_Auth
    #    OUTPUTS: None
    #    ACCESS: All user accounts
    #    NOTE: None
    #    """
    #    pass

    #def disconnect_zs_volume(self,input_dict):
    #    """
    #    DESC: Set the login token.
    #    INPUTS: self object
    #            zs_token - generated from ZS_Auth
    #    OUTPUTS: None
    #    ACCESS: All user accounts
    #    NOTE: None
    #    """
    #    pass

##########instance power################
    def reboot_zs_instance(self,instance_id=None):
        """
        DESC: Set the login token.
        INPUTS: self object
                zs_token - generated from ZS_Auth
        OUTPUTS: None
        ACCESS: All user accounts
        NOTE: None
        """
        pass

    def powercyle_zs_instance(self,input_dict):
        """
        DESC: Set the login token.
        INPUTS: self object
                zs_token - generated from ZS_Auth
        OUTPUTS: None
        ACCESS: All user accounts
        NOTE: None
        """
       # power on
       # power off
        pass

#############instance DR############33
    def snapshot_zs_instance(self,instance_id=None):
        """
        DESC: Set the login token.
        INPUTS: self object
                zs_token - generated from ZS_Auth
        OUTPUTS: None
        ACCESS: All user accounts
        NOTE: None
        """
        pass

    def delete_zs_instance_snapshot(self):
        pass

    def clone_zs_instance(self):
        pass

class ZS_Network(object):
    _client = None
    _project_id = None
    #Ex. Instructer usees IP tabels to configure a gateway - one side on internet other side 2 subnets on the other side. Build out  avirtual tree network
    #had this working before queens, set up vm with 3 nics, tell each nic what ip to use,

    def __init__(self, zs_connection):
        self.zs_net_mgr = zs_connection

    def client(self):
        pass

    def set_client(self, client):
        self._client = client

    def set_project_id(self, project_id):
        self._project_id = project_id

    def router_list(self):
        return filter(self._owned_resource,
                      self._client().list_routers()['routers'])

    def router_interfaces_list(self, router):
        return self._client.list_ports(device_id=router['id'])['ports']

    def port_list(self):
        return self.client().list_ports()['ports']

    def network_list(self):
        return filter(self._owned_resource,
                      self.client().list_networks()['networks'])

    def secgroup_list(self):
        return filter(self._owned_resource,
                      self.client().list_security_groups()['security_groups'])

    def floatingip_list(self):
        return filter(self._owned_resource,
                      self.client().list_floatingips()['floatingips'])

    def subnet_list(self):
        return filter(self._owned_resource,
                      self.client().list_subnets()['subnets'])

    def _owned_resource(self, res):
        # Only considering resources owned by project
        return res['tenant_id'] == self._project_id

class ZS_Storage(object):
    def create_zs_volume():
        pass

    def list_zs_volumes():
        pass

    def get_zs_volume():
        pass

    def delete_zs_volume():
        pass

    def attach_zs_volume():
        pass

    def detach_zs_volume():
        pass

    def snapshot_zs_volume():
        pass

    def list_zs_volume_snapshots():
        pass

    def get_zs_volume_snapshot():
        pass

    def delete_zs_snapshot():
        pass

#class ZS_ObjectStorage(object):
#    pass

#class ZS_Apps(object):
#    def list_apps():
#        pass
#    def get_app():
#        pass
#    def deploy_app():
#        pass
#    def upload_app_template():
#        pass
#    def delete_app():
#        pass

#class ZS_DNS(object):
#    pass

#class ZS_Image(object):
#    pass

#class ZS_Hosts(object):
#    pass
