Puppet::Parser::Functions.newfunction(:ceph_get_version, :type => :rvalue) do |args|
  require 'json'

  service_type = args[0]
  ids = args[1]
  id = '*'

  # Since all ids are on the current node, just take first
  id = ids[0] if ids

  version_string = Puppet::Util::Execution.execute("ceph tell #{service_type}.#{id} version -f json")
  versions = JSON.parse(version_string)
  versions
end

