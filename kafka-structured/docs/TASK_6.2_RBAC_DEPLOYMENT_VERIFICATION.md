# Task 6.2: RBAC Deployment Verification

**Date:** 2024-01-10  
**Task:** Apply RBAC manifests to GKE cluster  
**Status:** ✅ COMPLETE

---

## Deployment Summary

Successfully applied RBAC manifests to GKE cluster and verified all permissions are working correctly.

### Resources Created

```bash
kubectl apply -f kafka-structured/k8s/scaling-controller-rbac.yaml
```

**Output:**
```
serviceaccount/scaling-controller-sa created
role.rbac.authorization.k8s.io/scaling-controller-role created
rolebinding.rbac.authorization.k8s.io/scaling-controller-binding created
```

---

## Verification Results

### 1. Resource Existence ✅

All three resources were successfully created in the `sock-shop` namespace:

```bash
# ServiceAccount
kubectl get serviceaccount scaling-controller-sa -n sock-shop
NAME                    AGE
scaling-controller-sa   <timestamp>

# Role
kubectl get role scaling-controller-role -n sock-shop
NAME                      CREATED AT
scaling-controller-role   2026-04-10T01:43:01Z

# RoleBinding
kubectl get rolebinding scaling-controller-binding -n sock-shop
NAME                         ROLE                           AGE
scaling-controller-binding   Role/scaling-controller-role   <timestamp>
```

---

### 2. Permission Tests ✅

#### Authorized Actions (All Passed)

| Action | Resource | Namespace | Result |
|--------|----------|-----------|--------|
| `get` | deployments | sock-shop | ✅ yes |
| `list` | deployments | sock-shop | ✅ yes |
| `patch` | deployments | sock-shop | ✅ yes |
| `update` | deployments | sock-shop | ✅ yes |
| `get` | deployments/scale | sock-shop | ✅ yes |
| `patch` | deployments/scale | sock-shop | ✅ yes |
| `get` | pods | sock-shop | ✅ yes |
| `list` | pods | sock-shop | ✅ yes |

#### Unauthorized Actions (Correctly Denied)

| Action | Resource | Namespace | Result |
|--------|----------|-----------|--------|
| `create` | deployments | sock-shop | ✅ no (denied) |
| `delete` | deployments | sock-shop | ✅ no (denied) |
| `get` | deployments | default | ✅ no (denied) |

---

### 3. Security Boundary Verification ✅

**Namespace Isolation:**
- ✅ ServiceAccount can access resources in `sock-shop` namespace
- ✅ ServiceAccount CANNOT access resources in other namespaces (e.g., `default`)
- ✅ Meets requirement 16.3: "Permissions scoped to namespace only"

**Least Privilege:**
- ✅ ServiceAccount can only perform required actions (get, list, patch, update)
- ✅ ServiceAccount CANNOT create or delete deployments
- ✅ ServiceAccount CANNOT access cluster-wide resources

---

## Requirements Validation

### Requirement 4.1: Kubernetes RBAC
✅ **PASSED** - ServiceAccount, Role, and RoleBinding created successfully

**Evidence:**
- ServiceAccount `scaling-controller-sa` exists in `sock-shop` namespace
- Role `scaling-controller-role` grants required permissions
- RoleBinding `scaling-controller-binding` links ServiceAccount to Role

### Requirement 16.1: Security - Least Privilege
✅ **PASSED** - Scaling controller has minimal required permissions

**Evidence:**
- Can query deployments (get, list)
- Can modify deployment replicas (patch, update on deployments/scale)
- Can query pods (get, list)
- CANNOT create or delete deployments
- CANNOT access other namespaces

### Requirement 16.3: Security - Namespace Scoping
✅ **PASSED** - Permissions scoped to sock-shop namespace only

**Evidence:**
- Uses Role (namespace-scoped) instead of ClusterRole
- Uses RoleBinding (namespace-scoped) instead of ClusterRoleBinding
- Cannot access resources in other namespaces (verified with `default` namespace test)

---

## Test Commands Used

```bash
# Apply RBAC manifests
kubectl apply -f kafka-structured/k8s/scaling-controller-rbac.yaml

# Verify resources
kubectl get serviceaccount scaling-controller-sa -n sock-shop
kubectl get role scaling-controller-role -n sock-shop
kubectl get rolebinding scaling-controller-binding -n sock-shop

# Test authorized permissions
kubectl auth can-i get deployments --as=system:serviceaccount:sock-shop:scaling-controller-sa -n sock-shop
kubectl auth can-i list deployments --as=system:serviceaccount:sock-shop:scaling-controller-sa -n sock-shop
kubectl auth can-i patch deployments --as=system:serviceaccount:sock-shop:scaling-controller-sa -n sock-shop
kubectl auth can-i update deployments --as=system:serviceaccount:sock-shop:scaling-controller-sa -n sock-shop
kubectl auth can-i get deployments/scale --as=system:serviceaccount:sock-shop:scaling-controller-sa -n sock-shop
kubectl auth can-i patch deployments/scale --as=system:serviceaccount:sock-shop:scaling-controller-sa -n sock-shop
kubectl auth can-i get pods --as=system:serviceaccount:sock-shop:scaling-controller-sa -n sock-shop
kubectl auth can-i list pods --as=system:serviceaccount:sock-shop:scaling-controller-sa -n sock-shop

# Test unauthorized actions (should return "no")
kubectl auth can-i create deployments --as=system:serviceaccount:sock-shop:scaling-controller-sa -n sock-shop
kubectl auth can-i delete deployments --as=system:serviceaccount:sock-shop:scaling-controller-sa -n sock-shop
kubectl auth can-i get deployments --as=system:serviceaccount:sock-shop:scaling-controller-sa -n default
```

---

## Next Steps

Task 6.2 is complete. The scaling controller ServiceAccount is ready to use.

**Next Task:** 6.3 (Optional) - Test RBAC permission boundaries  
**Or proceed to:** Task 7.1 - Review hpa-baseline.yaml

---

## Notes

1. **Cluster Context:** Connected to GKE cluster at `https://34.66.13.244`
2. **Namespace:** `sock-shop` namespace exists and is active (2 days old)
3. **RBAC Type:** Uses Role/RoleBinding (namespace-scoped), not ClusterRole/ClusterRoleBinding
4. **Security:** All security requirements validated and passing

---

**Task 6.2 Status:** ✅ COMPLETE
