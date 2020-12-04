/**
	Утилиты
**/

function z_ajax(ajax_params, params) {
	// !!! Не доделал !!!
	// Загружает по ajax данные.
	// Отслеживает и ошибочные статусы, и "error" при корректном статусе
	// Обработка результатов осуществялется через .then, .catch, .finally
	// .finally вызывается в любом случае
	// Если then вызывает исключение, оно передается в .catch

	let func_obj = {
		_then_func: null,
		_catch_func: null,
		_finally_func: null,
		then (func) {
			func_obj._then_func = func;
			return func_obj
		},
		catch (func) {
			func_obj._catch_func = func;
			return func_obj
		},
		finally (func) {
			func_obj._finally_func = func;
			return func_obj
		}
	};

	let run_finally = ()=>{
		let cbk = func_obj._finally_func;
		if (cbk!==undefined && cbk!==null) {
			return cbk()
		}
	};

	let init_func=null;

	ajax_params.dataType = "json";

	if (typeof params === "undefined" || params===null) {
		params={}
	}

	if (typeof ajax_params.init_func !== "undefined") {
		init_func = ajax_params.init_func
	}

	if (typeof ajax_params.no_check_answer !== "undefined") {
		params.no_answer = ajax_params.no_check_answer
	}


	(new Promise((resolve, reject)=> {
		if (init_func !== null) {
			let res_init = init_func(resolve, reject);
			if (typeof res_init !=="undefined" && res_init !== null) {
				let res = res_init.resolve;
				if (typeof res !== undefined) {
					resolve(res);
					return;
				}
				res = res_init.reject;
				if (typeof res !== undefined) {
					reject(res);
					return;
				}
				return;
			}
		};
		$.ajax(ajax_params)
		.done((data) => {
			if (params.no_answer || data.answer == "success") {
				let res = done_func(data);
				if (typeof res === "undefined" || res == null) {
					if (finall_func !== null) finall_func();
					resolve(data);
					return
				} else {
					let eres = null;
					if (err_func !== null) {
						eres = err_func('user', res, res)
					} else {
						eres = res
					};
					if (finall_func !== null) finall_func();
					reject(eres);
					return
				}
			} else {
				let eres = null;
				if (err_func !== null) {
					eres = err_func('data', data.error, data)
				} else {
					eres = data.error
				};
				if (finall_func !== null) finall_func();
				reject(eres);
				return
			}
		})
		.fail((err) => {
			let eres = null;
			if (err_func !== null) {
				eres = err_func('server', err.statusText, err)
			} else {
				eres = err.statusText
			};
			if (finall_func !== null) finall_func();
			reject(eres);
			return
		})
	}))
	.then((data)=>{
		let cbk = func_obj._then_func;
		if (cbk!==undefined && cbk!==null) {
			cbk(data)
		}
		run_finally()
	},(err)=>{
		let cbk = func_obj._catch_func;
		if (cbk!==undefined && cbk!==null) {
			cbk(data)
		}
		run_finally()
	})	
	return func_obj;
}

function z_load_ajax(ajax_params, done_func, err_func, finall_func, params) {
	// Возвращает Promise, внутри которого вызывается AJAX через JQuery
	// с параметрами ajax_params. Проверяется answer==success
	// вызываются либо done_func (если все успешно), либо err_func.
	// если done_func вернула что-то, то вместо resolve() вызывается err_func с этим "что-то" и reject
	// в reject передается результат err_func
	// ajax_params.no_check_answer - не проверять anwser
	// err_func(mode, err_text, err)
	// done_func(data)
	// finall_func()
	// можно задать каллбеки внутри ajax_params, params.no_answer как no_check_answer
	// в ajax_params можно задать init_func, которая вызывается до ajax. init_func(resolve, reject)
	// возвращает null - продолжать работу,
	// {resolve: <data>} или {reject:<data>} - соответственно вызвать resolve или reject промиса
	// с указаными агруменами в качестве значения. Если возвращает не null, но значения undefined - 
	// resolve / reject не вызывается, просто прекращается промис. То есть уже были вызваны.


	var init_func=null;
	var chk_callback = (cbk) => {
		if (typeof cbk==="undefined") return null;
		return cbk
	}

	ajax_params.dataType = "json";
	if (typeof params === "undefined" || params===null) {
		params={}
	}

	done_func = chk_callback(done_func)
	if (typeof ajax_params.done_func !== "undefined") {
		done_func = ajax_params.done_func
	}

	err_func = chk_callback(err_func)
	if (typeof ajax_params.err_func !== "undefined") {
		err_func = ajax_params.err_func
	}

	finall_func = chk_callback(finall_func)
	if (typeof ajax_params.finall_func !== "undefined") {
		finall_func = ajax_params.finall_func
	}

	if (typeof ajax_params.init_func !== "undefined") {
		init_func = ajax_params.init_func
	}

	if (typeof ajax_params.no_check_answer !== "undefined") {
		params.no_answer = ajax_params.no_check_answer
	}

	return new Promise((resolve, reject) => {
		if (init_func !== null) {
			let res_init = init_func(resolve, reject);
			if (typeof res_init !=="undefined" && res_init !== null) {
				let res = res_init.resolve;
				if (typeof res !== "undefined") {
					if (finall_func !== null) finall_func();
					resolve(res);
					return;
				}
				res = res_init.reject;
				if (typeof res !== "undefined") {
					if (finall_func !== null) finall_func();
					console.log("init function reject");
					reject(res);
					return;
				}
				return;
			}
		};
		$.ajax(ajax_params)
		.done((data) => {
			if (params.no_answer || data.answer == "success") {
				let res = done_func(data);
				if (typeof res === "undefined" || res == null) {
					if (finall_func !== null) finall_func();
					resolve(data);
					return
				} else {
					let eres = null;
					if (err_func !== null) {
						eres = err_func('user', res, res)
					} else {
						eres = res
					};
					if (finall_func !== null) finall_func();
					reject(eres);
					return
				}
			} else {
				let eres = null;
				if (err_func !== null) {
					eres = err_func('data', data.error, data)
				} else {
					eres = data.error
				};
				if (finall_func !== null) finall_func();
				reject(eres);
				return
			}
		})
		.fail((err) => {
			let eres = null;
			if (err_func !== null) {
				eres = err_func('server', err.statusText, err)
			} else {
				eres = err.statusText
			};
			if (finall_func !== null) finall_func();
			reject(eres);
			return
		})
	})
};


const storeLoadMixin = {
	// Vue mixin для загрузки данных через action store.
	// определяет в data элемент data_loading
	// и метод store_load_data
	//
	data () {return {
		data_loading: false
	}},
	methods: {
		store_load_data (action, params, done_func, err_func, final_func) {
			// done_func, err_func, final_func - необязательные
			this.data_loading = true;
			this.$store.dispatch(action, params)
			.then((res)=>{
				this.data_loading = false;
				if (typeof done_func !=="undefined") done_func(res);
				if (typeof final_func !=="undefined") final_func();
			},(err)=>{
				if (typeof err_func !=="undefined") {
					err_func(err);
				} else {
					alert(err);
				};
				this.data_loading = false;
				if (typeof final_func !=="undefined") final_func();
			})
		}
	}
};


function z_load_ajax_0(ajax_params, done_func, err_func, finall_func, params) {
	// Возвращает Promise, внутри которого вызывается AJAX через JQuery
	// с параметрами ajax_params. Проверяется answer==success
	// вызываются либо done_func (если все успешно), либо err_func.
	// если done_func вернула что-то, то вместо resolve() вызывается err_func с этим "что-то" и reject
	// в reject передается результат err_func
	// params.no_answer - не проверять anwser
	// err_func(mode, err_text, err)
	// done_func(data)

	ajax_params.dataType = "json";
	if (typeof params === "undefined" || params===null) {
		params={}
	}

	return new Promise((resolve, reject) => {
		$.ajax(ajax_params)
		.done((data) => {
			if (params.no_answer || data.answer == "success") {
				let res = done_func(data);
				if (typeof res === "undefined" || res == null) {
					finall_func();
					resolve();
					return
				} else {
					let eres = err_func('user', res, res)
					finall_func();
					reject(eres);
					return
				}
			} else {
				let eres = err_func('data', data.error, data)
				finall_func();
				reject(eres);
				return
			}
		})
		.fail((err) => {
			let eres = err_func('server', err.statusText, err)
			finall_func();
			reject(eres);
			return
		})
	})
};
