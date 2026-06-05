class SeamIndex < Formula
  include Language::Python::Virtualenv

  desc "Local-first semantic codebase index for AI agents"
  homepage "https://github.com/Aditya190803/seam"
  url "https://files.pythonhosted.org/packages/source/s/seam-index/seam_index-0.1.0.tar.gz"
  sha256 "REPLACE_WITH_RELEASE_SHA256"
  license "MIT"

  depends_on "python@3.12"

  resource "fastmcp" do
    url "https://files.pythonhosted.org/packages/source/f/fastmcp/fastmcp-3.4.0.tar.gz"
    sha256 "REPLACE_WITH_FASTMCP_SHA256"
  end

  # Add pinned Python resources with `brew update-python-resources seam-index`
  # before publishing the tap.

  def install
    virtualenv_install_with_resources
  end

  test do
    assert_match "Seam", shell_output("#{bin}/seam --help")
  end
end
