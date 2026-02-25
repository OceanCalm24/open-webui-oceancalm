import { WEBUI_API_BASE_URL } from '$lib/constants';

export type Tenant = {
	id: string;
	name: string;
	slug: string;
	is_active: boolean;
	settings: Record<string, unknown> | null;
	created_at: number;
};

export type TenantForm = {
	name: string;
	slug: string;
	settings?: Record<string, unknown>;
};

export type TenantUpdateForm = {
	name?: string;
	is_active?: boolean;
	settings?: Record<string, unknown>;
};

export type TenantUser = {
	id: string;
	name: string;
	email: string;
	role: string;
	tenant_id: string | null;
};

export type AddTenantUserForm = {
	email: string;
	name: string;
	password: string;
	role?: string;
};

export const getTenants = async (token: string): Promise<Tenant[]> => {
	const error = await fetch(`${WEBUI_API_BASE_URL}/tenants/`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json() as Promise<Tenant[]>;
		})
		.catch((err) => {
			throw err;
		});
	return error;
};

export const createTenant = async (token: string, form: TenantForm): Promise<Tenant> => {
	const error = await fetch(`${WEBUI_API_BASE_URL}/tenants/`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify(form)
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json() as Promise<Tenant>;
		})
		.catch((err) => {
			throw err;
		});
	return error;
};

export const updateTenant = async (
	token: string,
	tenantId: string,
	form: TenantUpdateForm
): Promise<Tenant> => {
	const error = await fetch(`${WEBUI_API_BASE_URL}/tenants/${tenantId}`, {
		method: 'PATCH',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify(form)
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json() as Promise<Tenant>;
		})
		.catch((err) => {
			throw err;
		});
	return error;
};

export const deleteTenant = async (token: string, tenantId: string): Promise<boolean> => {
	const error = await fetch(`${WEBUI_API_BASE_URL}/tenants/${tenantId}`, {
		method: 'DELETE',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return true;
		})
		.catch((err) => {
			throw err;
		});
	return error;
};

export const getTenantUsers = async (token: string, tenantId: string): Promise<TenantUser[]> => {
	const error = await fetch(`${WEBUI_API_BASE_URL}/tenants/${tenantId}/users`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json() as Promise<TenantUser[]>;
		})
		.catch((err) => {
			throw err;
		});
	return error;
};

export const addTenantUser = async (
	token: string,
	tenantId: string,
	form: AddTenantUserForm
): Promise<TenantUser> => {
	const error = await fetch(`${WEBUI_API_BASE_URL}/tenants/${tenantId}/users`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify(form)
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json() as Promise<TenantUser>;
		})
		.catch((err) => {
			throw err;
		});
	return error;
};
