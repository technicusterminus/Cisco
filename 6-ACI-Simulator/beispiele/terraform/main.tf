# Terraform mit dem ACI-Provider gegen den Simulator.
# Aufruf: terraform init && terraform apply
terraform {
  required_providers {
    aci = {
      source = "CiscoDevNet/aci"
    }
  }
}

provider "aci" {
  username = "admin"
  password = "admin"
  url      = "http://localhost:8080"
  insecure = true
}

resource "aci_tenant" "tf" {
  name        = "Terraform"
  description = "angelegt mit Terraform"
}

resource "aci_vrf" "prod" {
  tenant_dn = aci_tenant.tf.id
  name      = "Prod"
}

resource "aci_bridge_domain" "web" {
  tenant_dn          = aci_tenant.tf.id
  name               = "BD-Web"
  relation_fv_rs_ctx = aci_vrf.prod.id
}

resource "aci_subnet" "web" {
  parent_dn = aci_bridge_domain.web.id
  ip        = "10.40.10.1/24"
  scope     = ["private"]
}

resource "aci_application_profile" "shop" {
  tenant_dn = aci_tenant.tf.id
  name      = "Webshop"
}

resource "aci_application_epg" "web" {
  application_profile_dn = aci_application_profile.shop.id
  name                   = "Web"
  relation_fv_rs_bd      = aci_bridge_domain.web.id
}
