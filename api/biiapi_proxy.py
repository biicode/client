from biicode.common.utils.bii_logging import logger
from biicode.common.model.symbolic.reference import References, ReferencedResources
from biicode.common.exception import NotInStoreException, NotFoundException, BiiException
from biicode.common.api.biiapi import BiiAPI
from biicode.common.model.version_tag import DEV
from biicode.client.exception import ConnectionErrorException


class BiiAPIProxy(BiiAPI):
    """Caching in disk BiiAPI implementation
    """

    def __init__(self, localdb, restapi_manager, user_io):
        self._store = localdb
        self._restapi_manager = restapi_manager
        self._out = user_io.out
        self._dev_versions = {}
        self._retrieved_blocks = set()  # transient, just for output

    def _store_login(self, user, token):
        self._store.set_login(user, token)

    def check_valid(self, block_versions, publish=True):
        """ This method is used BEFORE publication, to ensure that the parent versions in cache
        are coherent with server ones
        param block_versions: the versions of the PARENTS of the blocks currently under edition
        """
        invalid_versions = False
        for block_version in block_versions:
            # Initial versions are always empty, no problem
            if block_version.time == -1:
                continue
            # if we dont have it cached, no problem
            try:
                delta = self._store.get_delta_info(block_version)
            except NotInStoreException:
                continue
            try:
                ndelta = self._restapi_manager.get_version_delta_info(block_version)
            except:
                ndelta = None
            # If the cached delta does not match server one, invalidate cache and warn
            if delta != ndelta:
                invalid_versions = True
                self._store.remove_dev_references(block_version)
                if publish:
                    self._out.warn("Your ancestor %s in cache doesn't match server one"
                                   % str(block_version))
                    self._out.warn("The block %s was probably deleted on server, "
                                   "the cache has been updated" % block_version.block_name)
                else:
                    self._out.info("%s updated in cache" % block_version.to_pretty())
        if invalid_versions and publish:
            raise BiiException("There was a cache mismatch due to deleted blocks. You might "
                               "want to check your diff 'bii diff' or just retry")

    @property
    def user_name(self):
        '''Returns username of the previously authenticated user'''
        login = self._store.get_login()
        return login[0]

    def get_cells_snapshot(self, block_version):
        self.get_version_delta_info(block_version)
        try:
            return self._store.get_cells_snapshot(block_version)
        except NotInStoreException:
            remote_snap = self._restapi_manager.get_cells_snapshot(block_version)
            self._store.create_cells_snapshot(block_version, remote_snap)
            return remote_snap

    def get_dep_table(self, block_version):
        if self.get_version_delta_info(block_version):
            try:
                return self._store.get_dep_table(block_version)
            except NotInStoreException:
                remote_table = self._restapi_manager.get_dep_table(block_version)
                self._store.set_dep_table(block_version, remote_table)
                return remote_table
        else:
            return None

    def get_published_resources(self, references):
        '''Returns published resources from given ids
        @param references: list of ids
        '''
        def _get_not_found_refs(requested_refs, found_refs):
            not_found_refs = References()
            for block_version, cell_names in requested_refs.iteritems():
                version_resources = found_refs.get(block_version, {})
                missing = cell_names.difference(version_resources)
                if missing:
                    not_found_refs[block_version] = missing
            return not_found_refs

        # Read from localDB first, if not present, read from remote and catch!
        for block_version in references.keys():
            try:
                self.get_version_delta_info(block_version)
            except NotFoundException:
                self._out.error("Block %s has been deleted from server"
                                        % str(block_version))
                references.pop(block_version)
        local_refs = self._store.get_published_resources(references)
        not_found_refs = _get_not_found_refs(references, local_refs)

        # Read from remote building references
        remote_refs = ReferencedResources()
        if len(not_found_refs) > 0:
            logger.info("NOT In localdb: %s" % str(not_found_refs))
            for ref in not_found_refs:
                if ref.block not in self._retrieved_blocks:
                    self._out.info("Downloading files from: %s" % ref.block.to_pretty())
                    self._retrieved_blocks.add(ref.block)
            remote_refs = self._restapi_manager.get_published_resources(not_found_refs)

        # Cache return in local database (and prepare return)
        if len(remote_refs) > 0:
            logger.debug("Remote read: %r" % remote_refs.explode().keys())
            self._store.create_published_resources(remote_refs)

        all_refs = local_refs + remote_refs
        not_found_refs = _get_not_found_refs(references, all_refs)
        if not_found_refs:
            self._out.error("The following files "
                            "could not be retrieved %s" % not_found_refs)

        return all_refs

    def get_renames(self, brl_block, t1, t2):
        '''return a Renames object (i.e. a dict{oldName:newName}'''
        return self._restapi_manager.get_renames(brl_block, t1, t2)

    def publish(self, publish_request):
        return self._restapi_manager.publish(publish_request)

    def get_version_delta_info(self, block_version):
        if block_version.time == -1:
            return None
        try:
            return self._dev_versions[block_version]
        except KeyError:
            pass

        assert block_version.time is not None
        try:
            delta = self._store.get_delta_info(block_version)
            if delta.tag == DEV:
                try:
                    ndelta = self._restapi_manager.get_version_delta_info(block_version)
                    if delta != ndelta:
                        self._store.remove_dev_references(block_version)
                        self._store.upsert_delta_info(block_version, ndelta)
                        delta = ndelta
                        if ndelta.tag == DEV:
                            self._out.info("Dev version of %s has been updated"
                                                   % str(block_version))
                except (ConnectionErrorException, NotFoundException) as e:
                    self._out.warn('You depend on DEV version "%s", but unable to '
                                           'check updates in server: %s'
                                           % (str(block_version), str(e)))
        except NotInStoreException:
            delta = self._restapi_manager.get_version_delta_info(block_version)
            if delta.tag == DEV:  # Ensure we delete the references we can have because they can be outdated
                self._store.remove_dev_references(block_version)

            self._store.upsert_delta_info(block_version, delta)

        self._dev_versions[block_version] = delta
        return delta

    def get_version_by_tag(self, brl_block, version_tag):
        return self._restapi_manager.get_version_by_tag(brl_block, version_tag)

    def get_block_info(self, brl_block):
        return self._restapi_manager.get_block_info(brl_block)

    def find(self, finder_request, response):
        return self._restapi_manager.find(finder_request, response)

    def get_server_info(self):
        return self._restapi_manager.get_server_info()

    def require_auth(self):
        return self._restapi_manager.require_auth()

    def authenticate(self, user, password):
        return self._restapi_manager.authenticate(user, password)
