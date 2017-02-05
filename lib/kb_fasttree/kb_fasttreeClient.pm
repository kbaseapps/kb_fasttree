package kb_fasttree::kb_fasttreeClient;

use JSON::RPC::Client;
use POSIX;
use strict;
use Data::Dumper;
use URI;
use Bio::KBase::Exceptions;
my $get_time = sub { time, 0 };
eval {
    require Time::HiRes;
    $get_time = sub { Time::HiRes::gettimeofday() };
};

use Bio::KBase::AuthToken;

# Client version should match Impl version
# This is a Semantic Version number,
# http://semver.org
our $VERSION = "0.1.0";

=head1 NAME

kb_fasttree::kb_fasttreeClient

=head1 DESCRIPTION


** A KBase module: kb_fasttree
**
** This module runs FastTree to make Trees for either DNA or PROTEIN MSAs
**


=cut

sub new
{
    my($class, $url, @args) = @_;
    

    my $self = {
	client => kb_fasttree::kb_fasttreeClient::RpcClient->new,
	url => $url,
	headers => [],
    };

    chomp($self->{hostname} = `hostname`);
    $self->{hostname} ||= 'unknown-host';

    #
    # Set up for propagating KBRPC_TAG and KBRPC_METADATA environment variables through
    # to invoked services. If these values are not set, we create a new tag
    # and a metadata field with basic information about the invoking script.
    #
    if ($ENV{KBRPC_TAG})
    {
	$self->{kbrpc_tag} = $ENV{KBRPC_TAG};
    }
    else
    {
	my ($t, $us) = &$get_time();
	$us = sprintf("%06d", $us);
	my $ts = strftime("%Y-%m-%dT%H:%M:%S.${us}Z", gmtime $t);
	$self->{kbrpc_tag} = "C:$0:$self->{hostname}:$$:$ts";
    }
    push(@{$self->{headers}}, 'Kbrpc-Tag', $self->{kbrpc_tag});

    if ($ENV{KBRPC_METADATA})
    {
	$self->{kbrpc_metadata} = $ENV{KBRPC_METADATA};
	push(@{$self->{headers}}, 'Kbrpc-Metadata', $self->{kbrpc_metadata});
    }

    if ($ENV{KBRPC_ERROR_DEST})
    {
	$self->{kbrpc_error_dest} = $ENV{KBRPC_ERROR_DEST};
	push(@{$self->{headers}}, 'Kbrpc-Errordest', $self->{kbrpc_error_dest});
    }

    #
    # This module requires authentication.
    #
    # We create an auth token, passing through the arguments that we were (hopefully) given.

    {
	my $token = Bio::KBase::AuthToken->new(@args);
	
	if (!$token->error_message)
	{
	    $self->{token} = $token->token;
	    $self->{client}->{token} = $token->token;
	}
        else
        {
	    #
	    # All methods in this module require authentication. In this case, if we
	    # don't have a token, we can't continue.
	    #
	    die "Authentication failed: " . $token->error_message;
	}
    }

    my $ua = $self->{client}->ua;	 
    my $timeout = $ENV{CDMI_TIMEOUT} || (30 * 60);	 
    $ua->timeout($timeout);
    bless $self, $class;
    #    $self->_validate_version();
    return $self;
}




=head2 run_FastTree

  $return = $obj->run_FastTree($params)

=over 4

=item Parameter and return types

=begin html

<pre>
$params is a kb_fasttree.FastTree_Params
$return is a kb_fasttree.FastTree_Output
FastTree_Params is a reference to a hash where the following keys are defined:
	workspace_name has a value which is a kb_fasttree.workspace_name
	desc has a value which is a string
	input_ref has a value which is a kb_fasttree.data_obj_ref
	output_name has a value which is a kb_fasttree.data_obj_name
	species_tree_flag has a value which is an int
	intree has a value which is a kb_fasttree.data_obj_name
	fastest has a value which is an int
	pseudo has a value which is an int
	gtr has a value which is an int
	wag has a value which is an int
	noml has a value which is an int
	nome has a value which is an int
	cat has a value which is an int
	nocat has a value which is an int
	gamma has a value which is an int
workspace_name is a string
data_obj_ref is a string
data_obj_name is a string
FastTree_Output is a reference to a hash where the following keys are defined:
	report_name has a value which is a kb_fasttree.data_obj_name
	report_ref has a value which is a kb_fasttree.data_obj_ref
	output_ref has a value which is a kb_fasttree.data_obj_ref

</pre>

=end html

=begin text

$params is a kb_fasttree.FastTree_Params
$return is a kb_fasttree.FastTree_Output
FastTree_Params is a reference to a hash where the following keys are defined:
	workspace_name has a value which is a kb_fasttree.workspace_name
	desc has a value which is a string
	input_ref has a value which is a kb_fasttree.data_obj_ref
	output_name has a value which is a kb_fasttree.data_obj_name
	species_tree_flag has a value which is an int
	intree has a value which is a kb_fasttree.data_obj_name
	fastest has a value which is an int
	pseudo has a value which is an int
	gtr has a value which is an int
	wag has a value which is an int
	noml has a value which is an int
	nome has a value which is an int
	cat has a value which is an int
	nocat has a value which is an int
	gamma has a value which is an int
workspace_name is a string
data_obj_ref is a string
data_obj_name is a string
FastTree_Output is a reference to a hash where the following keys are defined:
	report_name has a value which is a kb_fasttree.data_obj_name
	report_ref has a value which is a kb_fasttree.data_obj_ref
	output_ref has a value which is a kb_fasttree.data_obj_ref


=end text

=item Description

Method for Tree building of either DNA or PROTEIN sequences
**
**        input_type: MSA
**        output_type: Tree

=back

=cut

 sub run_FastTree
{
    my($self, @args) = @_;

# Authentication: required

    if ((my $n = @args) != 1)
    {
	Bio::KBase::Exceptions::ArgumentValidationError->throw(error =>
							       "Invalid argument count for function run_FastTree (received $n, expecting 1)");
    }
    {
	my($params) = @args;

	my @_bad_arguments;
        (ref($params) eq 'HASH') or push(@_bad_arguments, "Invalid type for argument 1 \"params\" (value was \"$params\")");
        if (@_bad_arguments) {
	    my $msg = "Invalid arguments passed to run_FastTree:\n" . join("", map { "\t$_\n" } @_bad_arguments);
	    Bio::KBase::Exceptions::ArgumentValidationError->throw(error => $msg,
								   method_name => 'run_FastTree');
	}
    }

    my $url = $self->{url};
    my $result = $self->{client}->call($url, $self->{headers}, {
	    method => "kb_fasttree.run_FastTree",
	    params => \@args,
    });
    if ($result) {
	if ($result->is_error) {
	    Bio::KBase::Exceptions::JSONRPC->throw(error => $result->error_message,
					       code => $result->content->{error}->{code},
					       method_name => 'run_FastTree',
					       data => $result->content->{error}->{error} # JSON::RPC::ReturnObject only supports JSONRPC 1.1 or 1.O
					      );
	} else {
	    return wantarray ? @{$result->result} : $result->result->[0];
	}
    } else {
        Bio::KBase::Exceptions::HTTP->throw(error => "Error invoking method run_FastTree",
					    status_line => $self->{client}->status_line,
					    method_name => 'run_FastTree',
				       );
    }
}
 
  
sub status
{
    my($self, @args) = @_;
    if ((my $n = @args) != 0) {
        Bio::KBase::Exceptions::ArgumentValidationError->throw(error =>
                                   "Invalid argument count for function status (received $n, expecting 0)");
    }
    my $url = $self->{url};
    my $result = $self->{client}->call($url, $self->{headers}, {
        method => "kb_fasttree.status",
        params => \@args,
    });
    if ($result) {
        if ($result->is_error) {
            Bio::KBase::Exceptions::JSONRPC->throw(error => $result->error_message,
                           code => $result->content->{error}->{code},
                           method_name => 'status',
                           data => $result->content->{error}->{error} # JSON::RPC::ReturnObject only supports JSONRPC 1.1 or 1.O
                          );
        } else {
            return wantarray ? @{$result->result} : $result->result->[0];
        }
    } else {
        Bio::KBase::Exceptions::HTTP->throw(error => "Error invoking method status",
                        status_line => $self->{client}->status_line,
                        method_name => 'status',
                       );
    }
}
   

sub version {
    my ($self) = @_;
    my $result = $self->{client}->call($self->{url}, $self->{headers}, {
        method => "kb_fasttree.version",
        params => [],
    });
    if ($result) {
        if ($result->is_error) {
            Bio::KBase::Exceptions::JSONRPC->throw(
                error => $result->error_message,
                code => $result->content->{code},
                method_name => 'run_FastTree',
            );
        } else {
            return wantarray ? @{$result->result} : $result->result->[0];
        }
    } else {
        Bio::KBase::Exceptions::HTTP->throw(
            error => "Error invoking method run_FastTree",
            status_line => $self->{client}->status_line,
            method_name => 'run_FastTree',
        );
    }
}

sub _validate_version {
    my ($self) = @_;
    my $svr_version = $self->version();
    my $client_version = $VERSION;
    my ($cMajor, $cMinor) = split(/\./, $client_version);
    my ($sMajor, $sMinor) = split(/\./, $svr_version);
    if ($sMajor != $cMajor) {
        Bio::KBase::Exceptions::ClientServerIncompatible->throw(
            error => "Major version numbers differ.",
            server_version => $svr_version,
            client_version => $client_version
        );
    }
    if ($sMinor < $cMinor) {
        Bio::KBase::Exceptions::ClientServerIncompatible->throw(
            error => "Client minor version greater than Server minor version.",
            server_version => $svr_version,
            client_version => $client_version
        );
    }
    if ($sMinor > $cMinor) {
        warn "New client version available for kb_fasttree::kb_fasttreeClient\n";
    }
    if ($sMajor == 0) {
        warn "kb_fasttree::kb_fasttreeClient version is $svr_version. API subject to change.\n";
    }
}

=head1 TYPES



=head2 workspace_name

=over 4



=item Description

** The workspace object refs are of form:
**
**    objects = ws.get_objects([{'ref': params['workspace_id']+'/'+params['obj_name']}])
**
** "ref" means the entire name combining the workspace id and the object name
** "id" is a numerical identifier of the workspace or object, and should just be used for workspace
** "name" is a string identifier of a workspace or object.  This is received from Narrative.


=item Definition

=begin html

<pre>
a string
</pre>

=end html

=begin text

a string

=end text

=back



=head2 data_obj_name

=over 4



=item Definition

=begin html

<pre>
a string
</pre>

=end html

=begin text

a string

=end text

=back



=head2 data_obj_ref

=over 4



=item Definition

=begin html

<pre>
a string
</pre>

=end html

=begin text

a string

=end text

=back



=head2 FastTree_Params

=over 4



=item Description

FastTree Input Params


=item Definition

=begin html

<pre>
a reference to a hash where the following keys are defined:
workspace_name has a value which is a kb_fasttree.workspace_name
desc has a value which is a string
input_ref has a value which is a kb_fasttree.data_obj_ref
output_name has a value which is a kb_fasttree.data_obj_name
species_tree_flag has a value which is an int
intree has a value which is a kb_fasttree.data_obj_name
fastest has a value which is an int
pseudo has a value which is an int
gtr has a value which is an int
wag has a value which is an int
noml has a value which is an int
nome has a value which is an int
cat has a value which is an int
nocat has a value which is an int
gamma has a value which is an int

</pre>

=end html

=begin text

a reference to a hash where the following keys are defined:
workspace_name has a value which is a kb_fasttree.workspace_name
desc has a value which is a string
input_ref has a value which is a kb_fasttree.data_obj_ref
output_name has a value which is a kb_fasttree.data_obj_name
species_tree_flag has a value which is an int
intree has a value which is a kb_fasttree.data_obj_name
fastest has a value which is an int
pseudo has a value which is an int
gtr has a value which is an int
wag has a value which is an int
noml has a value which is an int
nome has a value which is an int
cat has a value which is an int
nocat has a value which is an int
gamma has a value which is an int


=end text

=back



=head2 FastTree_Output

=over 4



=item Description

FastTree Output


=item Definition

=begin html

<pre>
a reference to a hash where the following keys are defined:
report_name has a value which is a kb_fasttree.data_obj_name
report_ref has a value which is a kb_fasttree.data_obj_ref
output_ref has a value which is a kb_fasttree.data_obj_ref

</pre>

=end html

=begin text

a reference to a hash where the following keys are defined:
report_name has a value which is a kb_fasttree.data_obj_name
report_ref has a value which is a kb_fasttree.data_obj_ref
output_ref has a value which is a kb_fasttree.data_obj_ref


=end text

=back



=cut

package kb_fasttree::kb_fasttreeClient::RpcClient;
use base 'JSON::RPC::Client';
use POSIX;
use strict;

#
# Override JSON::RPC::Client::call because it doesn't handle error returns properly.
#

sub call {
    my ($self, $uri, $headers, $obj) = @_;
    my $result;


    {
	if ($uri =~ /\?/) {
	    $result = $self->_get($uri);
	}
	else {
	    Carp::croak "not hashref." unless (ref $obj eq 'HASH');
	    $result = $self->_post($uri, $headers, $obj);
	}

    }

    my $service = $obj->{method} =~ /^system\./ if ( $obj );

    $self->status_line($result->status_line);

    if ($result->is_success) {

        return unless($result->content); # notification?

        if ($service) {
            return JSON::RPC::ServiceObject->new($result, $self->json);
        }

        return JSON::RPC::ReturnObject->new($result, $self->json);
    }
    elsif ($result->content_type eq 'application/json')
    {
        return JSON::RPC::ReturnObject->new($result, $self->json);
    }
    else {
        return;
    }
}


sub _post {
    my ($self, $uri, $headers, $obj) = @_;
    my $json = $self->json;

    $obj->{version} ||= $self->{version} || '1.1';

    if ($obj->{version} eq '1.0') {
        delete $obj->{version};
        if (exists $obj->{id}) {
            $self->id($obj->{id}) if ($obj->{id}); # if undef, it is notification.
        }
        else {
            $obj->{id} = $self->id || ($self->id('JSON::RPC::Client'));
        }
    }
    else {
        # $obj->{id} = $self->id if (defined $self->id);
	# Assign a random number to the id if one hasn't been set
	$obj->{id} = (defined $self->id) ? $self->id : substr(rand(),2);
    }

    my $content = $json->encode($obj);

    $self->ua->post(
        $uri,
        Content_Type   => $self->{content_type},
        Content        => $content,
        Accept         => 'application/json',
	@$headers,
	($self->{token} ? (Authorization => $self->{token}) : ()),
    );
}



1;
