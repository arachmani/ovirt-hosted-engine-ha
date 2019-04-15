# constants for hosted-engine.conf options
ENGINE = 'he_local'
BROKER = 'broker'
HE_CONF = 'he_shared'
LEGACY_VM_CONF = 'legacyvmconf'

DOMAIN_TYPE = 'domainType'
ENGINE_FQDN = 'fqdn'
CONFIGURED = 'configured'
GATEWAY_ADDR = 'gateway'
HOST_ID = 'host_id'
SD_UUID = 'sdUUID'
SP_UUID = 'spUUID'
VDSM_SSL = 'vdsm_use_ssl'
BRIDGE_NAME = 'bridge'
VM_DISK_IMG_ID = 'vm_disk_id'
VM_DISK_VOL_ID = 'vm_disk_vol_id'
METADATA_VOLUME_UUID = 'metadata_volume_UUID'
METADATA_IMAGE_UUID = 'metadata_image_UUID'
LOCKSPACE_VOLUME_UUID = 'lockspace_volume_UUID'
LOCKSPACE_IMAGE_UUID = 'lockspace_image_UUID'
CONF_VOLUME_UUID = 'conf_volume_UUID'
CONF_IMAGE_UUID = 'conf_image_UUID'
CONF_FILE = 'conf'
HEVMID = 'vmid'
STORAGE = 'storage'
MNT_OPTIONS = 'mnt_options'
NFS_VERSION = 'nfs_version'
CONNECTIONUUID = 'connectionUUID'
# The following are used only for iSCSI storage
ISCSI_IQN = 'iqn'
ISCSI_PORTAL = 'portal'
ISCSI_USER = 'user'
ISCSI_PASSWORD = 'password'
ISCSI_PORT = 'port'
ISCSI_MPATHS_BLACKLIST = 'iscsi_paths_blacklist'
NETWORK_TEST = 'network_test'
TCP_T_ADDRESS = 'tcp_t_address'
TCP_T_PORT = 'tcp_t_port'

ENGINE_OPTIONAL_KEYS = [
    ISCSI_MPATHS_BLACKLIST,
    NETWORK_TEST,
    TCP_T_ADDRESS,
    TCP_T_PORT,
]

# constants for vm.conf options
VM = 'vm'
VM_UUID = 'vmId'
MEM_SIZE = 'memSize'

# constants for ha.conf options
HA = 'ha'
LOCAL_MAINTENANCE = 'local_maintenance'
LOCAL_MAINTENANCE_MANUAL = 'local_maintenance_manual'
