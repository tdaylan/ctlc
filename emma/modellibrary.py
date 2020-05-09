# :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
# 
# keras autoencoder model and plotting functions
# emma feb 2020
# 
# * convolutional autoencoder
# * autoencoder
#
#
# ::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::: 

import os
import pdb
import matplotlib.pyplot as plt
import numpy as np

# :: autoencoder ::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

def autoencoder(x_train, x_test, params, input_rms=False, rms_train=False,
                rms_test=False, supervised = False, num_classes=False, 
                y_train=False, y_test=False, split_lc=False,
                orbit_gap=[8794, 8795], simple=False):
    '''If supervised = True, must provide y_train, y_test, num_classes'''
    from keras import optimizers
    import keras.metrics
    from keras.models import Model
    from keras.layers import Dense, concatenate

    # -- encoding -------------------------------------------------------------
    if split_lc:
        x_train_0,x_train_1 = x_train[:,:orbit_gap[0]],x_train[:,orbit_gap[1]:]
        x_test_0,x_test_1 = x_test[:,:orbit_gap[0]],x_test[:,orbit_gap[1]:]
        encoded = encoder_split([x_train_0, x_train_1], params)
    else:
       if simple:
            encoded = simple_encoder(x_train, params)
       else:
            encoded = encoder(x_train, params)
    
    if input_rms:
        mlp = create_mlp(np.shape(rms_train)[1])
        shared_input = concatenate([mlp.output,encoded.output])
        shared_output = Dense(params['latent_dim'],
                              activation='relu')(shared_input)

    # -- supervised: softmax --------------------------------------------------
    if supervised:
        if input_rms:
            x = Dense(num_classes, activation='softmax')(shared_output)
            model = Model(inputs=[encoded.input,mlp.input], outputs=x)
        else:
            x = Dense(num_classes,
                  activation='softmax')(encoded.output)
            model = Model(encoded.input, x)
        model.summary()
        
        
    else: # -- decoding -------------------------------------------------------
        if split_lc:
            decoded = decoder_split(x_train, encoded.output, params)
        else:
            if simple:
                decoded = simple_decoder(x_train, encoded.output, params)
            else:
                decoded = decoder(x_train, encoded.output, params)
        model = Model(encoded.input, decoded)
        print(model.summary())
        
    # -- compile model --------------------------------------------------------
        
    if params['optimizer'] == 'adam':
        opt = optimizers.adam(lr = params['lr'], 
                              decay=params['lr']/params['epochs'])
    elif params['optimizer'] == 'adadelta':
        opt = optimizers.adadelta(lr = params['lr'])
        
    model.compile(optimizer=opt, loss=params['losses'],
                  metrics=['accuracy', keras.metrics.Precision(),
                  keras.metrics.Recall()])

    # -- train model ----------------------------------------------------------
    
    if supervised and input_rms:
        history = model.fit([x_train, rms_train], y_train,
                            epochs=params['epochs'],
                            batch_size=params['batch_size'], shuffle=True)
    elif supervised and not input_rms:
        history = model.fit(x_train, y_train, epochs=params['epochs'],
                            batch_size=params['batch_size'], shuffle=True)
    elif input_rms and not supervised:
        history = model.fit([x_train, rms_train], x_train,
                            epochs=params['epochs'],
                            batch_size=params['batch_size'], shuffle=True)
    else:
        history = model.fit(x_train, x_train, epochs=params['epochs'],
                            batch_size=params['batch_size'], shuffle=True,
                            validation_data=(x_test, x_test))
        
    return history, model

def simple_encoder(x_train, params):
    from keras.layers import Input, Dense, Flatten
    from keras.models import Model
    input_dim = np.shape(x_train)[1]
    input_img = Input(shape = (input_dim,1))
    x = Flatten()(input_img)
    encoded = Dense(params['latent_dim'], activation='relu')(x)
    encoder = Model(input_img, encoded)
    return encoder

def simple_decoder(x_train, bottleneck, params):
    from keras.layers import Dense, Reshape
    input_dim = np.shape(x_train)[1]
    x = Dense(input_dim, activation='sigmoid')(bottleneck)
    decoded = Reshape((input_dim, 1))(x)
    return decoded

def encoder(x_train, params):
    from keras.layers import Input, Conv1D, MaxPooling1D, Dropout, Flatten
    from keras.layers import Dense, AveragePooling1D
    from keras.models import Model
    
    input_dim = np.shape(x_train)[1]
    num_iter = int(params['num_conv_layers']/2)
    
    input_img = Input(shape = (input_dim, 1))
    for i in range(num_iter):
        if i == 0:
            x = Conv1D(params['num_filters'][i], params['kernel_size'][i],
                    activation=params['activation'], padding='same')(input_img)
        else:
            x = Conv1D(params['num_filters'][i], params['kernel_size'][i],
                        activation=params['activation'], padding='same')(x)
        x = MaxPooling1D(2, padding='same')(x)
        # x = AveragePooling1D(2, padding='same')(x)
        
        x = Dropout(params['dropout'])(x)
        
        x = MaxPooling1D([params['num_filters'][i]],
                          data_format='channels_first')(x)
        # x = AveragePooling1D([params['num_filters'][i]],
        #                      data_format='channels_first')(x)
    
    x = Flatten()(x)
    encoded = Dense(params['latent_dim'], activation=params['activation'])(x)
    
    encoder = Model(input_img, encoded)

    return encoder

def encoder_split(x, params):
    from keras.layers import Input, Conv1D, MaxPooling1D, Dropout, Flatten
    from keras.layers import Dense, concatenate
    from keras.models import Model
    
    num_iter = int((params['num_conv_layers'])/2)
    
    input_imgs = [Input(shape=(np.shape(a)[1], 1)) for a in x]

    for i in range(num_iter):
        conv_1 = Conv1D(params['num_filters'][i], params['kernel_size'][i],
             activation=params['activation'], padding='same')
        x = [conv_1(a) for a in input_imgs]
        maxpool_1 = MaxPooling1D(2, padding='same')
        x = [maxpool_1(a) for a in x]
        dropout_1 = Dropout(params['dropout'])
        x = [dropout_1(a) for a in x]
        maxchannel_1 = MaxPooling1D([params['num_filters'][i]],
                                    data_format='channels_first')
        x = [maxchannel_1(a) for a in x]

    flatten_1 = Flatten()
    x = [flatten_1(a) for a in x]
    dense_1 = Dense(params['latent_dim'], activation=params['activation'])
    x = [dense_1(a) for a in x]
    encoded = concatenate(x)
    encoder = Model(inputs=input_imgs, outputs=encoded)
    return encoder

def decoder(x_train, bottleneck, params):
    from keras.layers import Dense, Reshape, Conv1D, UpSampling1D, Dropout
    from keras.layers import Lambda
    from keras import backend as K
    input_dim = np.shape(x_train)[1]
    num_iter = int(params['num_conv_layers']/2)
    
    x = Dense(int(input_dim/(2**(num_iter))))(bottleneck)
    x = Reshape((int(input_dim/(2**(num_iter))), 1))(x)
    for i in range(num_iter):
        x = Lambda(lambda x: \
                   K.repeat_elements(x,params['num_filters'][num_iter+i],2))(x)
        x = Dropout(params['dropout'])(x)
        x = UpSampling1D(2)(x)
        if i == num_iter-1:
            decoded = Conv1D(1, params['kernel_size'][num_iter],
                             activation=params['last_activation'],
                             padding='same')(x)
        else:
            x = Conv1D(1, params['kernel_size'][num_iter+i],
                       activation=params['activation'], padding='same')(x)
    return decoded

def decoder_split(x_train, bottleneck, params):
    from keras.layers import Dense, Reshape, Conv1D, UpSampling1D, Dropout
    from keras.layers import Lambda, concatenate
    from keras import backend as K
    
    input_dim = np.shape(x_train)[1]
    num_iter = int((params['num_conv_layers'])/2)
    
    dense_1 = Dense(int(input_dim/(2**(num_iter))))
    x = [dense_1(bottleneck), dense_1(bottleneck)]
    reshape_1 = Reshape((int(input_dim/(2**(num_iter))), 1))
    x = [reshape_1(a) for a in x]
    for i in range(num_iter):
        upsampling_channels = Lambda(lambda x: \
                    K.repeat_elements(x,params['num_filters'][num_iter+i],2))
        x = [upsampling_channels(a) for a in x]
        dropout_1 = Dropout(params['dropout'])(x)
        x = [dropout_1(a) for a in x]
        upsampling_1 = UpSampling1D(2)(x)
        x = [upsampling_1(a) for a in x]
        if i == num_iter-1:
            conv_2 = Conv1D(1, params['kernel_size'][num_iter+1],
                              activation=params['last_activation'],
                              padding='same')
            x = [conv_2(a) for a in x]
            decoded = concatenate(x)
        else:
            conv_1 = Conv1D(1, params['kernel_size'][num_iter+i],
                        activation=params['activation'], padding='same')
            x = [conv_1(a) for a in x]
    return decoded

def create_mlp(input_dim):
    '''Build multi-layer perceptron neural network model for numerical data
    (rms)'''
    from keras.models import Model
    from keras.layers import Dense, Input
    input_img = Input(shape = (input_dim,))
    x = Dense(8, activation='relu')(input_img)
    x = Dense(4, activation='relu')(x)
    x = Dense(1, activation='linear')(x)
    
    model = Model(input_img, x)
    return model
    
# :: preprocessing data :::::::::::::::::::::::::::::::::::::::::::::::::::::::

def split_data(flux, time, p, train_test_ratio = 0.9, cutoff=16336,
               supervised=False, classes=False, interpolate=False):

    # >> truncate (must be a multiple of 2**num_conv_layers)
    new_length = int(np.shape(flux)[1] / \
                 (2**(np.max(p['num_conv_layers'])/2)))*\
                 int((2**(np.max(p['num_conv_layers'])/2)))
    flux=np.delete(flux,np.arange(new_length,np.shape(flux)[1]),1)
    time = time[:new_length]

    # >> split test and train data
    if supervised:
        train_inds = []
        test_inds = []
        class_types, counts = np.unique(classes, return_counts=True)
        num_classes = len(class_types)
        #  = min(counts)
        y_train = []
        y_test = []
        for i in range(len(class_types)):
            inds = np.nonzero(classes==i)[0]
            num_train = int(len(inds)*train_test_ratio)
            train_inds.extend(inds[:num_train])
            test_inds.extend(inds[num_train:])
            labels = np.zeros((len(inds), num_classes))
            labels[:,i] = 1.
            y_train.extend(labels[:num_train])
            y_test.extend(labels[num_train:])

        y_train = np.array(y_train)
        y_test - np.array(y_test)
        x_train = np.copy(flux[train_inds])
        x_test = np.copy(flux[test_inds])
    else:
        split_ind = int(train_test_ratio*np.shape(flux)[0])
        x_train = np.copy(flux[:split_ind])
        x_test = np.copy(flux[split_ind:])
        y_test, y_train = [False, False]
        
    if interpolate:
        train_data, time = interpolate_lc(np.concatenate([x_train, x_test]), time)
        x_train = train_data[:len(x_train)]
        x_test = train_data[len(x_train):]
        
    x_train =  np.resize(x_train, (np.shape(x_train)[0],
                                   np.shape(x_train)[1], 1))
    x_test =  np.resize(x_test, (np.shape(x_test)[0],
                                   np.shape(x_test)[1], 1))
    return x_train, x_test, y_train, y_test, time
    

def rms(x):
    rms = np.sqrt(np.mean(x**2, axis = 1))
    return rms

def standardize(x):
    cutoff = np.shape(x)[1]
    means = np.mean(x, axis = 1, keepdims=True) # >> subtract mean
    x = x - means
    stdevs = np.std(x, axis = 1, keepdims=True) # >> divide by standard dev
    x = x / stdevs   
    return x
    
def normalize(flux, time):
    medians = np.median(flux, axis = 1, keepdims=True)
    flux = flux / medians - 1.
    return flux, time

def interpolate_lc(flux, time, flux_err=False, interp_tol=20./(24*60),
                   num_sigma=5, orbit_gap_len = 3):
    '''Interpolates nan gaps less than 20 minutes long.'''
    from astropy.stats import SigmaClip
    from scipy import interpolate
    flux_interp = []
    for i in flux:
        # >> sigma clip
        sigclip = SigmaClip(sigma=num_sigma, maxiters=None, cenfunc='median')
        clipped_inds = np.nonzero(np.ma.getmask(sigclip(i, masked=True)))
        i[clipped_inds] = np.nan
        
        # >> find nan windows
        n = np.shape(i)[0]
        loc_run_start = np.empty(n, dtype=bool)
        loc_run_start[0] = True
        np.not_equal(np.isnan(i)[:-1], np.isnan(i)[1:], out=loc_run_start[1:])
        run_starts = np.nonzero(loc_run_start)[0]
    
        # >> find nan window lengths
        run_lengths = np.diff(np.append(run_starts, n))
        tdim = time[1]-time[0]
        
        # -- interpolate small nan gaps ---------------------------------------
        interp_gaps = np.nonzero((run_lengths * tdim <= interp_tol) * \
                                            np.isnan(i[run_starts]))
        interp_inds = run_starts[interp_gaps]
        interp_lens = run_lengths[interp_gaps]

        i_interp = np.copy(i)
        for a in range(np.shape(interp_inds)[0]):
            start_ind = interp_inds[a]
            end_ind = interp_inds[a] + interp_lens[a]
            i_interp[start_ind:end_ind] = np.interp(time[start_ind:end_ind],
                                                    time[np.nonzero(~np.isnan(i))],
                                                    i[np.nonzero(~np.isnan(i))])
        i = i_interp
        
        # -- spline interpolate large nan gaps --------------------------------
        interp_gaps = np.nonzero((run_lengths * tdim > interp_tol) * \
                                 (run_lengths*tdim < orbit_gap_len) * \
                                 np.isnan(i[run_starts]))
        interp_inds = run_starts[interp_gaps]
        interp_lens = run_lengths[interp_gaps]
        
        i_interp = np.copy(i)
        for a in range(np.shape(interp_inds)[0]):
            num_inds = np.nonzero(np.isnan(i)==False)
            tck = interpolate.splrep(time[num_inds], i[num_inds])
            
            start_ind, end_ind = interp_inds[a], interp_inds[a]+interp_lens[a]
            t_new = np.linspace(time[start_ind-1]+tdim, time[end_ind-1]+tdim,
                                end_ind-start_ind)
            i_interp[start_ind:end_ind]=interpolate.splev(t_new, tck)
        flux_interp.append(i_interp)
        
    # -- remove orbit nan gap -------------------------------------------------
    flux = np.array(flux_interp)
    nan_inds = np.nonzero(np.prod(np.isnan(flux)==False, 
                                  axis = 0) == False)
    time = np.delete(time, nan_inds)
    flux = np.delete(flux, nan_inds, 1)
    if type(flux_err) != bool:
        flux_err = np.delete(flux_err, nan_inds, 1)
        return flux, time, flux_err
    else:
        return flux, time

# :: fake data ::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

def gaussian(x, a, b, c):
    '''a = height, b = position of center, c = stdev'''
    import numpy as np
    return a * np.exp(-(x-b)**2 / (2*c**2))

def signal_data(training_size = 10000, test_size = 100, input_dim = 100,
                 time_max = 30., noise_level = 0.0, height = 1., center = 15.,
                 stdev = 0.8, h_factor = 0.2, center_factor = 5.,
                 reshape=True):
    '''Generate training data set with flat light curves and gaussian light
    curves, with variable height, center, noise level as a fraction of gaussian
    height)
    '''

    x = np.empty((training_size + test_size, input_dim))
    # y = np.empty((training_size + test_size))
    y = np.zeros((training_size + test_size, 2))
    l = int(np.shape(x)[0]/2)
    
    # >> no peak data
    x[:l] = np.zeros((l, input_dim))
    # y[:l] = 0.
    y[:l, 0] = 1.
    

    # >> with peak data
    time = np.linspace(0, time_max, input_dim)
    for i in range(l):
        a = height + h_factor*np.random.normal()
        b = center + center_factor*np.random.normal()
        x[l+i] = gaussian(time, a = a, b = b, c = stdev)
    # y[l:] = 1.
    y[l:, 1] = 1.

    # >> add noise
    x += np.random.normal(scale = noise_level, size = np.shape(x))
    
    # >> normalize
    # x = x / np.median(x, axis = 1, keepdims=True) - 1.

    # >> partition training and test datasets
    x_train = np.concatenate((x[:int(training_size/2)], 
                              x[l:-int(test_size/2)]))
    y_train = np.concatenate((y[:int(training_size/2)], 
                              y[l:-int(test_size/2)]))
    x_test = np.concatenate((x[int(training_size/2):l], 
                             x[-int(test_size/2):]))
    y_test = np.concatenate((y[int(training_size/2):l], 
                             y[-int(test_size/2):]))

    if reshape:
        x_train = np.reshape(x_train, (np.shape(x_train)[0],
                                       np.shape(x_train)[1], 1))
        x_test = np.reshape(x_test, (np.shape(x_test)[0],
                                     np.shape(x_test)[1], 1))

    return time, x_train, y_train, x_test, y_test

def no_signal_data(training_size = 10000, test_size = 100, input_dim = 100,
                   noise_level = 0., min0max1=True, reshape=False):
    import numpy as np

    x = np.empty((training_size + test_size, input_dim))
    y = np.empty((training_size + test_size))
    l = int(np.shape(x)[0]/2)
    
    # >> no peak data
    if min0max1:
        x = np.zeros(np.shape(x))
    else:
        x = np.ones(np.shape(x))
    y = 0.

    # >> add noise
    x += np.random.normal(scale = noise_level, size = np.shape(x))

    # >> partition training and test datasets
    x_train = np.concatenate((x[:int(training_size/2)], 
                              x[l:-int(test_size/2)]))
    y_train = np.concatenate((y[:int(training_size/2)], 
                              y[l:-int(test_size/2)]))
    x_test = np.concatenate((x[int(training_size/2):l], 
                             x[-int(test_size/2):]))
    y_test = np.concatenate((y[int(training_size/2):l], 
                             y[-int(test_size/2):]))

    if reshape:
        x_train = np.reshape(x_train, (np.shape(x_train)[0],
                                       np.shape(x_train)[1], 1))
        x_test = np.reshape(x_test, (np.shape(x_test)[0],
                                     np.shape(x_test)[1], 1))
    
    return x_train, y_train, x_test, y_test

# :: plotting :::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

def ticid_label(ax, ticid, title=False):
    '''https://arxiv.org/pdf/1905.10694.pdf'''
    from astroquery.mast import Catalogs

    target = 'TIC '+str(int(ticid))
    catalog_data = Catalogs.query_object(target, radius=0.02, catalog='TIC')
    Teff = catalog_data[0]["Teff"]
    rad = catalog_data[0]["rad"]
    mass = catalog_data[0]["mass"]
    GAIAmag = catalog_data[0]["GAIAmag"]
    d = catalog_data[0]["d"]
    Bmag = catalog_data[0]["Bmag"]
    Vmag = catalog_data[0]["Vmag"]
    objType = catalog_data[0]["objType"]
    Tmag = catalog_data[0]["Tmag"]
    lum = catalog_data[0]["lum"]

    info = target+'\nTeff {}\nrad {}\nmass {}\nGAIAmag {}\nd {}\nobjType {}'
    info1 = target+', Teff {}, rad {}, mass {},\nGAIAmag {}, d {}, objType {}'
    if title:
        ax.set_title(info1.format('%.3g'%Teff, '%.3g'%rad, '%.3g'%mass, 
                                  '%.3g'%GAIAmag, '%.3g'%d, objType),
                     fontsize='xx-small')
    else:
        ax.text(0.98, 0.98, info.format('%.3g'%Teff, '%.3g'%rad, '%.3g'%mass, 
                                        '%.3g'%GAIAmag, '%.3g'%d, objType),
                  transform=ax.transAxes, horizontalalignment='right',
                  verticalalignment='top', fontsize='xx-small')
    
def format_axes(ax):
    # >> force aspect = 3/8
    xlim, ylim = ax.get_xlim(), ax.get_ylim()
    ax.set_aspect(abs((xlim[1]-xlim[0])/(ylim[1]-ylim[0])*(3./8.)))
    
    if list(ax.get_xticklabels()) == []:
        ax.tick_params('x', bottom=False) # >> remove ticks if no label
    else:
        ax.tick_params('x', labelsize='small')
    ax.tick_params('y', labelsize='small')
    ax.ticklabel_format(useOffset=False)

def corner_plot(activation, p, n_bins = 50, log = True):
    '''Creates corner plot for latent space.
    '''
    from matplotlib.colors import LogNorm
    # latentDim = np.shape(activation)[1]
    latentDim = p['latent_dim']

    fig, axes = plt.subplots(nrows = latentDim, ncols = latentDim,
                             figsize = (10, 10))

    # >> deal with 1 latent dimension case
    if latentDim == 1:
        axes.hist(np.reshape(activation, np.shape(activation)[0]), n_bins,
                  log=log)
        axes.set_ylabel('\u03C61')
        axes.set_ylabel('frequency')
    else:
        # >> row 1 column 1 is first latent dimension (phi1)
        for i in range(latentDim):
            axes[i,i].hist(activation[:,i], n_bins, log=log)
            axes[i,i].set_aspect(aspect=1)
            for j in range(i):
                if log:
                    norm = LogNorm()
                axes[i,j].hist2d(activation[:,j], activation[:,i],
                                 bins=n_bins, norm=norm)
                # >> remove axis frame of empty plots
                axes[latentDim-1-i, latentDim-1-j].axis('off')

            # >> x and y labels
            axes[i,0].set_ylabel('\u03C6' + str(i))
            axes[latentDim-1,i].set_xlabel('\u03C6' + str(i))

        # >> removing axis
        for ax in axes.flatten():
            ax.set_xticks([])
            ax.set_yticks([])
        plt.subplots_adjust(hspace=0, wspace=0)

    return fig, axes

def input_output_plot(x, x_test, x_predict, out, ticid_test=False,
                      inds = [0, -14, -10, 1, 2], addend = 0., sharey=False,
                      mock_data=False):
    '''Plots input light curve, output light curve and the residual.
    !!Can only handle len(inds) divisible by 3 or 5'''
    # !! get rid of reshape parameter
    if len(inds) % 5 == 0:
        ncols = 5
    elif len(inds) % 3 == 0:
        ncols = 3
    ngroups = int(len(inds)/ncols)
    nrows = int(3*ngroups)
    fig, axes = plt.subplots(nrows, ncols, figsize=(15,12), sharey=sharey,
                             sharex=True)
    plt.subplots_adjust(hspace=0)
    for i in range(ncols):
        for ngroup in range(ngroups):
            ind = int(ngroup*ncols + i)
            if not mock_data:
                ticid_label(axes[ngroup*3,i], ticid_test[inds[ind]],title=True)
            axes[ngroup*3,i].plot(x,x_test[inds[ind]]+addend,'.k',markersize=2)
            axes[ngroup*3+1,i].plot(x,x_predict[inds[ind]]+addend,'.k',
                                    markersize=2)
            # >> residual
            residual = (x_test[inds[ind]] - x_predict[inds[ind]])
            axes[ngroup*3+2, i].plot(x, residual, '.k', markersize=2)
            for j in range(3):
                format_axes(axes[ngroup*3+j,i])
        axes[-1, i].set_xlabel('time [BJD - 2457000]', fontsize='small')
    for i in range(ngroups):
        axes[3*i,   0].set_ylabel('input\nrelative flux',  fontsize='small')
        axes[3*i+1, 0].set_ylabel('output\nrelative flux', fontsize='small')
        axes[3*i+2, 0].set_ylabel('residual', fontsize='small') 
    fig.tight_layout()
    plt.savefig(out)
    plt.close(fig)
    return fig, axes
    
def get_activations(model, x_test, input_rms = False, rms_test = False):
    from keras.models import Model
    layer_outputs = [layer.output for layer in model.layers][1:]
    activation_model = Model(inputs=model.input, outputs=layer_outputs)
    if input_rms:
        activations = activation_model.predict([x_test, rms_test])
    else:
        activations = activation_model.predict(x_test)
    return activations

def latent_space_plot(model, activations, params, out):
    # >> get ind for plotting latent space
    dense_inds = np.nonzero(['dense' in x.name for x in \
                                 model.layers])[0]
    # dense_inds = np.nonzero(['flatten' in x.name for x in model.layers])[0]
    for ind in dense_inds:
        if np.shape(activations[ind-1])[1] == params['latent_dim']:
            bottleneck_ind = ind - 1
    fig, axes = corner_plot(activations[bottleneck_ind-1], params)
    plt.savefig(out)
    plt.close(fig)
    return fig, axes

def kernel_filter_plot(model, out_dir):
    # >> get inds for plotting kernel and filters
    layer_inds = np.nonzero(['conv' in x.name for x in model.layers])[0]
    for a in layer_inds: # >> loop through conv layers
        filters, biases = model.layers[a].get_weights()
        fig, ax = plt.subplots()
        ax.imshow(np.reshape(filters, (np.shape(filters)[0],
                                       np.shape(filters)[2])))
        ax.set_xlabel('filter')
        ax.set_ylabel('kernel')
        plt.savefig(out_dir + 'layer' + str(a) + '.png')
        plt.close(fig)

def intermed_act_plot(x, model, activations, x_test, out_dir, addend=0.5,
                      inds = [0, -1], movie = True):
    '''Visualizing intermediate activations
    activation.shape = (test_size, input_dim, filter_num) = (116, 16272, 32)'''
    # >> get inds for plotting intermediate activations
    act_inds = np.nonzero(['conv' in x.name or \
                           'max_pool' in x.name or \
                           'dropout' in x.name or \
                           'reshape' in x.name for x in \
                           model.layers])[0]
    act_inds = np.array(act_inds) -1

    for c in range(len(inds)): # >> loop through light curves
        fig, axes = plt.subplots(figsize=(4,3))
        addend = 1. - np.median(x_test[inds[c]])
        axes.plot(np.linspace(np.min(x), np.max(x), np.shape(x_test)[1]),
                x_test[inds[c]] + addend, '.k', markersize=2)
        axes.set_xlabel('time [BJD - 2457000]')
        axes.set_ylabel('relative flux')
        plt.tight_layout()
        fig.savefig(out_dir+str(c)+'ind-0input.png')
        plt.close(fig)
        for a in act_inds: # >> loop through layers
            activation = activations[a]
            if np.shape(activation)[2] == 1:
                nrows = 1
                ncols = 1
            else:
                ncols = 4
                nrows = int(np.shape(activation)[2]/ncols)
            fig, axes = plt.subplots(nrows,ncols,figsize=(8*ncols*0.5,3*nrows))
            for b in range(np.shape(activation)[2]): # >> loop through filters
                if ncols == 1:
                    ax = axes
                else:
                    ax = axes.flatten()[b]
                x1 = np.linspace(np.min(x), np.max(x), np.shape(activation)[1])
                ax.plot(x1, activation[inds[c]][:,b]+addend,'.k',markersize=2)
            if nrows == 1:
                axes.set_xlabel('time [BJD - 2457000]')
                axes.set_ylabel('relative flux')
            else:
                for i in range(nrows):
                    axes[i,0].set_ylabel('relative\nflux')
                for j in range(ncols):
                    axes[-1,j].set_xlabel('time [BJD - 2457000]')
            fig.tight_layout()
            fig.savefig(out_dir+str(c)+'ind-'+str(a+1)+model.layers[a+1].name\
                        +'.png')
            plt.close(fig)

def epoch_plots(history, p, out_dir, supervised=True):
    label_list = [['loss', 'accuracy'], ['precision', 'recall']]
    key_list = [['loss', 'accuracy'], [list(history.history.keys())[-2],
                                       list(history.history.keys())[-1]]]
    for i in range(2):
        fig, ax1 = plt.subplots()
        ax2 = ax1.twinx()
        ax1.plot(history.history[key_list[i][0]], label=label_list[i][0])
        ax1.set_ylabel(label_list[i][0])
        ax2.plot(history.history[key_list[i][1]], '--', label=label_list[i][1])
        ax2.set_ylabel(label_list[i][1])
        ax1.set_xlabel('epoch')
        ax1.set_xticks(range(p['epochs']))
        ax1.tick_params('both', labelsize='x-small')
        ax2.tick_params('both', labelsize='x-small')
        fig.tight_layout()
        if i == 0:
            plt.savefig(out_dir + 'acc_loss.png')
        else:
            plt.savefig(out_dir + 'prec_recall.png')
        plt.close(fig)
    
def input_bottleneck_output_plot(x, x_test, x_predict, activations, model,
                                 ticid_test, out, inds=[0,1,-1,-2,-3],
                                 addend = 1., sharey=False, mock_data=False):
    '''Can only handle len(inds) divisible by 3 or 5'''
    bottleneck_ind = np.nonzero(['dense' in x.name for x in \
                                 model.layers])[0][0]
    bottleneck = activations[bottleneck_ind - 1]
    if len(inds) % 5 == 0:
        ncols = 5
    elif len(inds) % 3 == 0:
        ncols = 3
    ngroups = int(len(inds)/ncols)
    nrows = int(3*ngroups)
    fig, axes = plt.subplots(nrows, ncols, figsize=(15,5), sharey=sharey,
                             sharex=True)
    plt.subplots_adjust(hspace=0)
    for i in range(ncols):
        for ngroup in range(ngroups):
            ind = int(ngroup*ncols + i)
            axes[ngroup*3,i].plot(x,x_test[inds[ind]]+addend,'.k',markersize=2)
            axes[ngroup*3+1,i].plot(np.linspace(np.min(x),np.max(x),
                                              len(bottleneck[inds[ind]])),
                                              bottleneck[inds[ind]], '.k',
                                              markersize=2)
            axes[ngroup*3+2,i].plot(x,x_predict[inds[ind]]+addend,'.k',
                                    markersize=2)
            if not mock_data:
                ticid_label(axes[ngroup*3,i],ticid_test[inds[ind]], title=True)
            for j in range(3):
                format_axes(axes[ngroup*3+j,i])
        axes[-1, i].set_xlabel('time [BJD - 2457000]', fontsize='small')
    for i in range(ngroups):
        axes[3*i,   0].set_ylabel('input\nrelative flux',  fontsize='small')
        axes[3*i+1, 0].set_ylabel('bottleneck', fontsize='small')
        axes[3*i+2, 0].set_ylabel('output\nrelative flux', fontsize='small')
    fig.tight_layout()
    plt.savefig(out)
    plt.close(fig)
    return fig, axes
    

def movie(x, model, activations, x_test, p, out_dir, inds = [0, -1],
          addend=0.5):
    for c in range(len(inds)):
        fig, axes = plt.subplots(figsize=(8,3))
        ymin = []
        ymax = []
        for activation in activations:
            if np.shape(activation)[1] == p['latent_dim']:
                ymin.append(min(activation[inds[c]]))
                ymax.append(max(activation[inds[c]]))
            elif len(np.shape(activation)) > 2:
                if np.shape(activation)[2] == 1:
                    ymin.append(min(activation[inds[c]]))
                    ymax.append(max(activation[inds[c]]))
        ymin = np.min(ymin) + addend
        ymax = np.max(ymax) + addend
        addend = 1. - np.median(x_test[inds[c]])

        # >> plot input
        axes.plot(np.linspace(np.min(x), np.max(x), np.shape(x_test)[1]),
                  x_test[inds[c]] + addend, '.k', markersize=2)
        axes.set_xlabel('time [BJD - 2457000]')
        axes.set_ylabel('relative flux')
        axes.set_ylim(ymin=ymin, ymax=ymax)
        fig.tight_layout()
        fig.savefig('./image-000.png')

        # >> plot intermediate activations
        n=1
        for a in range(len(activations)):
            activation = activations[a]
            if np.shape(activation)[1] == p['latent_dim']:
                length = p['latent_dim']
                axes.cla()
                axes.plot(np.linspace(np.min(x), np.max(x), length),
                          activation[inds[c]] + addend, '.k', markersize=2)
                axes.set_xlabel('time [BJD - 2457000]')
                axes.set_ylabel('relative flux')
                axes.set_ylim(ymin=ymin, ymax =ymax)
                fig.tight_layout()
                fig.savefig('./image-' + f'{n:03}.png')
                n += 1
            elif len(np.shape(activation)) > 2:
                if np.shape(activation)[2] == 1:
                    length = np.shape(activation)[1]
                    y = np.reshape(activation[inds[c]], (length))
                    axes.cla()
                    axes.plot(np.linspace(np.min(x), np.max(x), length),
                              y + addend, '.k', markersize=2)
                    axes.set_xlabel('time [BJD - 2457000]')
                    axes.set_ylabel('relative flux')
                    axes.set_ylim(ymin = ymin, ymax = ymax)
                    fig.tight_layout()
                    fig.savefig('./image-' + f'{n:03}.png')
                    n += 1
        os.system('ffmpeg -framerate 2 -i ./image-%03d.png -pix_fmt yuv420p '+\
                  out_dir+str(c)+'ind-movie.mp4')

def latent_space_clustering(activation, x_test, x, ticid, out = './', 
                            n_bins = 50, addend=1., scatter = True):
    '''Clustering latent space
    '''
    from matplotlib.colors import LogNorm
    # from sklearn.cluster import DBSCAN
    from sklearn.neighbors import LocalOutlierFactor
    latentDim = np.shape(activation)[1]

    # -- calculate lof --------------------------------------------------------           
    clf = LocalOutlierFactor()
    clf.fit_predict(activation)
    lof = -1 * clf.negative_outlier_factor_
    inds = np.argsort(lof)[-20:] # >> outliers
    inds2 = np.argsort(lof)[:20] # >> inliers
    
    # >> deal with 1 latent dimension case
    if latentDim == 1: # TODO !!
        fig, axes = plt.subplots(figsize = (15,15))
        axes.hist(np.reshape(activation, np.shape(activation)[0]), n_bins,
                  log=True)
        axes.set_ylabel('\u03C61')
        axes.set_ylabel('frequency')
    else:


        # >> row 1 column 1 is first latent dimension (phi1)
        for i in range(latentDim):
            for j in range(i):
                z1, z2 = activation[:,j], activation[:,i]
                # X = np.array((z1, z2)).T                
                # clf = LocalOutlierFactor()
                # clf.fit_predict(X)
                # lof = -1 * clf.negative_outlier_factor_

                
                # -- plot latent space w/ inset plots -------------------------
                fig, ax = plt.subplots(figsize = (15,15))
                
                if scatter:
                    ax.plot(z1, z2, '.')
                else:
                    ax.hist2d(z1, z2, bins=n_bins, norm=LogNorm())
                
                plt.xticks(fontsize='xx-large')
                plt.yticks(fontsize='xx-large')
                
                h = 0.047
                x0 = 0.85
                y0 = 0.9
                xstep = h*8/3 + 0.025
                ystep = h + 0.025
                
                # >> sort to clean up plot
                inds0 = inds[:10]
                inds0 = sorted(inds, key=lambda z: ((z1[z]-np.max(z1))+\
                                                    (z2[z]-np.min(z2)))**2)
                
                for k in range(10):
                    # >> make inset axes
                    if k < 5:
                        axins = ax.inset_axes([x0 - k*xstep, y0, h*8/3, h])
                    else:
                        axins = ax.inset_axes([x0, y0 - (k-4)*ystep, h*8/3, h])
                    xp, yp = z1[inds0[k]], z2[inds0[k]]
            
                    xextent = ax.get_xlim()[1] - ax.get_xlim()[0]
                    yextent = ax.get_ylim()[1] - ax.get_ylim()[0]
                    x1, x2 = xp-0.01*xextent, xp+0.01*xextent
                    y1, y2 = yp-0.01*yextent, yp+0.01*yextent
                    axins.set_xlim(x1, x2)
                    axins.set_ylim(y1, y2)
                    ax.indicate_inset_zoom(axins)
                    
                    # >> plot light curves
                    axins.set_xlim(min(x), max(x))
                    axins.set_ylim(min(x_test[inds0[k]]),
                                   max(x_test[inds0[k]]))
                    axins.plot(x, x_test[inds0[k]] + addend, '.k',
                               markersize=2)
                    axins.set_xticklabels('')
                    axins.set_yticklabels('')
                    axins.patch.set_alpha(0.5)

                # >> x and y labels
                ax.set_ylabel('\u03C61' + str(i), fontsize='xx-large')
                ax.set_xlabel('\u03C61' + str(j), fontsize='xx-large')
                fig.savefig(out + 'phi' + str(j) + 'phi' + str(i) + '.png')
                
                # -- plot 20 light curves -------------------------------------
                # >> plot light curves with lof label
                fig1, ax1 = plt.subplots(20, figsize = (7,28))
                fig1.subplots_adjust(hspace=0)
                fig2, ax2 = plt.subplots(20, figsize = (7,28))
                fig2.subplots_adjust(hspace=0)
                fig3, ax3 = plt.subplots(20, figsize = (7,28))
                fig3.subplots_adjust(hspace=0)
                for k in range(20):
                    # >> outlier plot
                    ax1[k].plot(x,x_test[inds[19-k]]+addend,'.k',markersize=2)
                    ax1[k].set_xticks([])
                    ax1[k].set_ylabel('relative\nflux')
                    ax1[k].text(0.8, 0.65,
                                'LOF {}\nTIC {}'.format(str(lof[inds[19-k]])[:9],
                                                        str(int(ticid[inds[19-k]]))),
                                transform = ax1[k].transAxes)
                    
                    # >> inlier plot
                    ax2[k].plot(x, x_test[inds2[k]]+addend, '.k', markersize=2)
                    ax2[k].set_xticks([])
                    ax2[k].set_ylabel('rellative\nflux')
                    ax2[k].text(0.8, 0.65,
                                'LOF {}\nTIC {}'.format(str(lof[inds2[k]])[:9],
                                                        str(int(ticid[inds2[k]]))),
                                transform = ax2[k].transAxes)
                    
                    # >> random lof plot
                    ind = np.random.choice(range(len(lof)-1))
                    ax3[k].plot(x, x_test[ind] + addend, '.k', markersize=2)
                    ax3[k].set_xticks([])
                    ax3[k].set_ylabel('relative\nflux')
                    ax3[k].text(0.8, 0.65,
                                'LOF {}\nTIC {}'.format(str(lof[ind])[:9],
                                                        str(int(ticid[ind]))),
                                transform = ax3[k].transAxes)
                
                ax1[-1].set_xlabel('time [BJD - 2457000]')
                ax2[-1].set_xlabel('time [BJD - 2457000]')
                ax3[-1].set_xlabel('time [BJD - 2457000]')
                fig1.savefig(out + 'phi' + str(j) + 'phi' + str(i) + \
                            '-outliers.png')
                fig2.savefig(out + 'phi' + str(j) + 'phi' + str(i) + \
                             '-inliers.png')
                fig3.savefig(out + 'phi' + str(j) + 'phi'  + str(i) + \
                             '-randomlof.png')
                

        # >> removing axis
        # for ax in axes.flatten():
        #     ax.set_xticks([])
        #     ax.set_yticks([])
        # plt.subplots_adjust(hspace=0, wspace=0)

    return fig, ax

def training_test_plot(x, x_train, x_test, y_train_classes, y_test_classes,
                       y_predict, num_classes, out, ticid_train, ticid_test,
                       mock_data=False):
    # !! add more rows
    colors = ['r', 'g', 'b', 'm'] # !! add more colors
    # >> training data set
    fig, ax = plt.subplots(nrows = 7, ncols = num_classes, figsize=(15,10),
                           sharex=True)
    plt.subplots_adjust(hspace=0)
    # >> test data set
    fig1, ax1 = plt.subplots(nrows = 7, ncols = num_classes, figsize=(15,10),
                             sharex=True)
    plt.subplots_adjust(hspace=0)
    for i in range(num_classes): # >> loop through classes
        inds = np.nonzero(y_train_classes == i)[0]
        inds1 = np.nonzero(y_test_classes == i)[0]
        for j in range(min(7, len(inds))): # >> loop through rows
            ax[j,i].plot(x, x_train[inds[j]], '.'+colors[i], markersize=2)
            if not mock_data:
                ticid_label(ax[j,i], ticid_train[inds1[j]])
        for j in range(min(7, len(inds1))):
            ax1[j,i].plot(x, x_test[inds1[j]], '.'+colors[y_predict[inds1[j]]],
                          markersize=2)
            if not mock_data:
                ticid_label(ax1[j,i], ticid_test[inds1[j]])    
            ax1[j,i].text(0.98, 0.02, 'True: '+str(i)+'\nPredicted: '+\
                          str(y_predict[inds1[j]]),
                          transform=ax1[j,i].transAxes, fontsize='xx-small',
                          horizontalalignment='right',
                          verticalalignment='bottom')
    for i in range(num_classes):
        ax[0,i].set_title('True class '+str(i), color=colors[i])
        ax1[0,i].set_title('True class '+str(i), color=colors[i])
        
        for axis in [ax[-1,i], ax1[-1,i]]:
            axis.set_xlabel('time [BJD - 2457000]', fontsize='small')
    for j in range(7):
        for axis in [ax[j,0],ax1[j,0]]:
            axis.set_ylabel('relative\nflux', fontsize='small')
            
    for axis in  ax.flatten():
        format_axes(axis)
    for axis in ax1.flatten():
        format_axes(axis)
    # fig.tight_layout()
    # fig1.tight_layout()
    fig.savefig(out+'train.png')
    fig1.savefig(out+'test.png')



    
# def autoencoder_dual_input1(x_train, x_test, rms_train, rms_test, params,
#                             supervised=False, y_train = False, y_test=False,
#                             num_classes = False):
#     '''Adapted from: https://www.pyimagesearch.com/2019/02/04/keras-multiple-
#     inputs-and-mixed-data/'''
#     from keras.layers import concatenate
#     from keras.layers import Conv1D, Dense, Reshape
#     from keras.models import Model
#     from keras import optimizers
#     import keras.metrics
#     input_dim = np.shape(x_train)[1]
#     # >> create the MLP and autoencoder models
#     mlp = create_mlp(np.shape(rms_train)[1])
#     encoded = encoder1(x_train, params)
#     # autoencoder = create_conv_layers(x_train, params)

#     # x = Reshape((1,1))(mlp.output)
#     # x = concatenate([autoencoder.output, Reshape((1,1))(mlp.output)], axis = 1)
#     # x = Reshape((input_dim,))(autoencoder.output)
#     x = concatenate([mlp.output,
#                      Reshape((input_dim,))(encoded.output)], axis = 1)
#     # x = Reshape((input_dim+1,))(x)
    
    
#     # x = Dense(4, activation='relu')(combinedInput)
#     # x = Dense(1, activation='linear')(x)
#     x = Dense(input_dim, activation='relu')(x)
#     x = Reshape((input_dim,1))(x)
#     # x = Conv1D(1, params['kernel_size'], activation=params['last_activation'],
#     #            padding='same')(combinedInput)
#     if supervised:
#         x = Dense(num_classes,activation='softmax')(encoded.output)
#         model = Model(inputs=[encoded.input, mlp.input], output=x)
#         print(model.summary())
#     else:
#         model = Model(inputs=[encoded.input, mlp.input], outputs=x)
#         print(model.summary())
    
#     # !! find a better way to do this
#     if params['optimizer'] == 'adam':
#         opt = optimizers.adam(lr = params['lr'], 
#                               decay=params['lr']/params['epochs'])
#     elif params['optimizer'] == 'adadelta':
#         opt = optimizers.adadelta(lr = params['lr'])
        
#     model.compile(optimizer=opt, loss=params['losses'],
#                   metrics=['accuracy', keras.metrics.Precision(),
#                            keras.metrics.Recall()])
#     history = model.fit([x_train, rms_train], x_train, epochs=params['epochs'],
#                         batch_size=params['batch_size'], shuffle=True,
#                         validation_data=([x_test, rms_test], x_test))
#     return history, model

# def autoencoder_dual_input2(x_train, x_test, rms_train, rms_test, params,
#                             supervised=False, y_train=False, y_test=False,
#                             num_classes=False):
#     '''Adapted from: https://stackoverflow.com/questions/52435274/how-to-use-
#     keras-merge-layer-for-autoencoder-with-two-ouput'''
#     from keras.layers import concatenate
#     from keras.layers import Dense
#     from keras import optimizers
#     import keras.metrics
#     from keras.models import Model
    
#     # >> create the MLP and encoder models
#     mlp = create_mlp(np.shape(rms_train)[1])
#     encoded = encoder(x_train, params)

#     # >> shared representation layer
#     shared_input = concatenate([mlp.output,encoded.output])
#     shared_output = Dense(params['latent_dim'], activation='relu')(shared_input)
#     if supervised:
#         x = Dense(num_classes,activation='softmax')(shared_output)
#         model = Model(inputs=[encoded.input, mlp.input], output=x)
#         print(model.summary())
#     else:
#         decoded = decoder(x_train, shared_output, params)
#         model = Model(inputs=[encoded.input, mlp.input], outputs=decoded)
    
#     # >> get model
#     # model = Model(inputs=[encoded.input, mlp.input], outputs=decoded.output)
    
    
#     # !! find a better way to do this
#     if params['optimizer'] == 'adam':
#         opt = optimizers.adam(lr = params['lr'], 
#                               decay=params['lr']/params['epochs'])
#     elif params['optimizer'] == 'adadelta':
#         opt = optimizers.adadelta(lr = params['lr'])
        
#     model.compile(optimizer=opt, loss=params['losses'],
#                   metrics=['accuracy', keras.metrics.Precision(),
#                            keras.metrics.Recall()])
#     history = model.fit([x_train, rms_train], x_train, epochs=params['epochs'],
#                         batch_size=params['batch_size'], shuffle=True,
#                         validation_data=([x_test, rms_test], x_test))
#     return history, model
    
    
    
    # def encoder2(x_train, params):
#     '''https://towardsdatascience.com/applied-deep-learning-part-4
#     -convolutional-neural-networks-584bc134c1e2
#     stacked'''
#     from keras.layers import Input,Conv1D,MaxPooling1D,Dropout,Flatten,Dense
#     from keras.models import Model
    
#     input_dim = np.shape(x_train)[1]
#     num_iter = int((params['num_conv_layers'] - 1)/2)
    
#     input_img = Input(shape = (input_dim, 1))
#     x = Conv1D(params['num_filters'][0], params['kernel_size'],
#                activation=params['activation'], padding='same')(input_img)
#     for i in range(num_iter):
#         x = MaxPooling1D(2, padding='same')(x)
#         x = Dropout(params['dropout'])(x)
#         x = Conv1D(1, 1, activation='relu')(x)
#         # x = MaxPooling1D([params['num_filters'][i]],
#         #                  data_format='channels_first')(x)
#         x = Conv1D(params['num_filters'][1+i], params['kernel_size'],
#                    activation=params['activation'], padding='same')(x)
#         x = Conv1D(params['num_filters'][1+i], params['kernel_size'],
#                    activation=params['activation'], padding='same')(x)
#     x = MaxPooling1D([params['num_filters'][i]], 
#                      data_format='channels_first')(x)
#     x = Flatten()(x)
#     encoded = Dense(params['latent_dim'], activation=params['activation'])(x)
#     # return encoded
#     encoder = Model(input_img, encoded)
#     return encoder
    
    
    # def create_conv_layers(x_train, params, supervised = False):
#     from keras.layers import Input, Conv1D, MaxPooling1D, UpSampling1D
#     from keras.layers import Reshape, Dense, Flatten, Dropout
#     from keras.models import Model

#     input_dim = np.shape(x_train)[1]
#     num_iter = int((params['num_conv_layers'] - 1)/2)
    
#     input_img = Input(shape = (input_dim, 1))
#     x = Conv1D(params['num_filters'][0], params['kernel_size'],
#                 activation=params['activation'], padding='same')(input_img)
#     for i in range(num_iter):
#         x = MaxPooling1D(2, padding='same')(x)
#         x = Dropout(params['dropout'])(x)
#         x = MaxPooling1D([params['num_filters'][i]],
#                           data_format='channels_first')(x)
#         x = Conv1D(params['num_filters'][1+i], params['kernel_size'],
#                     activation=params['activation'], padding='same')(x)
#     x = MaxPooling1D([params['num_filters'][i]], 
#                       data_format='channels_first')(x)
#     x = Flatten()(x)
#     encoded = Dense(params['latent_dim'], activation=params['activation'])(x)

#     x = Dense(int(input_dim/(2**(i+1))))(encoded)
#     x = Reshape((int(input_dim/(2**(i+1))), 1))(x)
#     for i in range(num_iter):
#         x = Conv1D(params['num_filters'][num_iter+1], params['kernel_size'],
#                     activation=params['activation'], padding='same')(x)
#         x = UpSampling1D(2)(x)
#         x = Dropout(params['dropout'])(x)
#         x = MaxPooling1D([params['num_filters'][num_iter+1]],
#                           data_format='channels_first')(x)
#     decoded = Conv1D(1, params['kernel_size'],
#                       activation=params['last_activation'], padding='same')(x)
    
#     if supervised:
#         model = Model(input_img, encoded)
#         print(model.summary())
          
#     else:
#         model = Model(input_img, decoded)
#         print(model.summary())
    
#     return model
    
    # if inputs_before_after:
    #     orbit_gap_start = np.nonzero(time < orbit_gap[0])[0][-1]
    #     orbit_gap_end = np.nonzero(time > orbit_gap[1])[0][0]
    #     x_train_0 = x_train[:,:orbit_gap_start]
    #     x_train_1 = x_train[:,orbit_gap_end:]
    #     x_test_0 = x_test[:,:orbit_gap_start]
    #     x_test_1 = x_test[:,orbit_gap_end:]
    #     y_train_0, y_train_1 = [np.copy(y_train), np.copy(y_train)]
    #     y_test_0, y_test_1 = [np.copy(y_test), np.copy(y_test)]
    #     # x_train_0 = x_train[]
    #     return x_train_0, x_train_1, x_test_0, x_test_1, y_train_0, y_train_1,\
    #         y_test_0, y_test_1
    # else:
    
# def decoder(x_train, bottleneck, params):
#     '''042820
#     https://github.com/julienr/ipynb_playground/blob/master/keras/convmnist/keras_conv_autoencoder_mnist.ipynb
#     '''
#     from keras.layers import Dense  ,Reshape, Conv1D, UpSampling1D, Dropout
#     from keras.layers import MaxPooling1D
#     input_dim = np.shape(x_train)[1]
#     num_iter = int(params['num_conv_layers']/2)
    
#     # x = Dense(int(input_dim/(2**(num_iter))))(bottleneck)
#     x = Dense(int(input_dim/(2**num_iter) * \
#                   params['num_filters'][num_iter-1]))(bottleneck)
#     x = Reshape((int(input_dim/(2**(num_iter))),
#                  params['num_filters'][num_iter-1]))(x)
#     for i in range(num_iter):
#         x = UpSampling1D(2)(x)
#         # !!
#         x = Conv1D(params['num_filters'][num_iter+i],
#                    params['kernel_size'][num_iter+i],
#                    activation=params['activation'], padding='same')(x)
#     decoded = Conv1D(1, params['kernel_size'][num_iter+i],
#                      activation=params['last_activation'], padding='same')(x)
#     return decoded
    
    
# def encoder(x_train,params):
#     '''https://github.com/gabrieleilertsen/hdrcnn/blob/master/network.py'''
#     from keras.layers import Input, Conv1D, MaxPooling1D, Dropout, Flatten
#     from keras.layers import Dense
#     from keras.models import Model
    
#     input_dim = np.shape(x_train)[1]
#     # num_iter = int((params['num_conv_layers'] - 1)/2)
#     # num_iter = int(params['num_conv_layers']/2)
#     num_iter = int(params['num_conv_layers']/2)
    
#     input_img = Input(shape = (input_dim, 1))
#     for i in range(num_iter):
#         if i == 0:
#             x = Conv1D(params['num_filters'][i], params['kernel_size'][i],
#                    activation=params['activation'], padding='same')(input_img)
#         else:
#             x = Conv1D(params['num_filters'][i], params['kernel_size'][i],
#                        activation=params['activation'], padding='same')(x)
#         x = MaxPooling1D(2, padding='same')(x)
#     x = Flatten()(x)
#     # x = Dense(int(input_dim/(2**num_iter) * params['num_filters'][i]),
#     #           activation=params['activation'])(x)
#     encoded = Dense(params['latent_dim'], activation=params['activation'])(x)
#     encoder = Model(input_img, encoded)

#     return encoder

# def encoder(x_train,params):
#     '''https://github.com/gabrieleilertsen/hdrcnn/blob/master/network.py'''
#     from keras.layers import Input, Conv1D, MaxPooling1D, Dropout, Flatten
#     from keras.layers import Dense
#     from keras.models import Model
    
#     input_dim = np.shape(x_train)[1]
#     # num_iter = int((params['num_conv_layers'] - 1)/2)
#     # num_iter = int(params['num_conv_layers']/2)
#     num_iter = int(params['num_conv_layers']/2)
    
#     input_img = Input(shape = (input_dim, 1))
#     for i in range(num_iter):
#         if i == 0:
#             x = Conv1D(params['num_filters'][i], params['kernel_size'][i],
#                    activation=params['activation'], padding='same')(input_img)
#         else:
#             x = Conv1D(params['num_filters'][i], params['kernel_size'][i],
#                        activation=params['activation'], padding='same')(x)
#         x = Conv1D(params['num_filters'][i], params['kernel_size'][i],
#                    activation=params['activation'], padding='same')(x)
#         x = MaxPooling1D(2, padding='same')(x)
#     x = Flatten()(x)
#     # x = Dense(int(input_dim/(2**num_iter) * params['num_filters'][i]),
#     #           activation=params['activation'])(x)
#     encoded = Dense(params['latent_dim'], activation=params['activation'])(x)
#     encoder = Model(input_img, encoded)

#     return encoder


# def encoder(x_train, params):
#     from keras.layers import Input, Conv1D, MaxPooling1D, Dropout, Flatten
#     from keras.layers import Dense
#     from keras.models import Model
    
#     input_dim = np.shape(x_train)[1]
#     # num_iter = int((params['num_conv_layers'] - 1)/2)
#     # num_iter = int(params['num_conv_layers']/2)
#     num_iter = int(params['num_conv_layers']/2)
    
#     input_img = Input(shape = (input_dim, 1))
#     # x = Conv1D(params['num_filters'][0], params['kernel_size'][0],
#     #            activation=params['activation'], padding='same')(input_img)
#     for i in range(num_iter):
#         if i == 0:
#             x = Conv1D(params['num_filters'][i], params['kernel_size'][i],
#                    activation=params['activation'], padding='same')(input_img)
#         else:
#             x = Conv1D(params['num_filters'][i], params['kernel_size'][i],
#                        activation=params['activation'], padding='same')(x)
#         x = MaxPooling1D(2, padding='same')(x)
#     x = Flatten()(x)
#     # x = Dense(int(input_dim/(2**num_iter) * params['num_filters'][i]),
#     #           activation=params['activation'])(x)
#     encoded = Dense(params['latent_dim'], activation=params['activation'])(x)
#     encoder = Model(input_img, encoded)

#     return encoder  
    
# def decoder(x_train, bottleneck, params):
#     from keras.layers import Dense, Reshape, Conv1D, UpSampling1D, Dropout
#     from keras.layers import MaxPooling1D, Lambda
#     from keras import backend as K
#     input_dim = np.shape(x_train)[1]
#     num_iter = int(params['num_conv_layers']/2)
    
#     x = Dense(int(input_dim/(2**(num_iter))))(bottleneck)
#     x = Reshape((int(input_dim/(2**(num_iter))), 1))(x)
#     for i in range(num_iter):
#         x = Conv1D(params['num_filters'][num_iter+i],
#                     params['kernel_size'][num_iter+i],
#                     activation=params['activation'], padding='same')(x)
#         x = UpSampling1D(2)(x)
#         x = Dropout(params['dropout'])(x)
#         x = MaxPooling1D([params['num_filters'][num_iter+i]],
#                           data_format='channels_first')(x)


#     decoded = Conv1D(1, params['kernel_size'][num_iter+1],
#                       activation=params['last_activation'], padding='same')(x)
#     return decoded
    
    
# def encoder1(x_train, params):
#     '''https://machinelearningmastery.com/introduction-to-1x1-convolutions-to
#     -reduce-the-complexity-of-convolutional-neural-networks/
#     Using convolutions over channels to downsample feature maps'''
#     from keras.layers import Input,Conv1D,MaxPooling1D,Dropout,Flatten,Dense
#     from keras.models import Model
    
#     input_dim = np.shape(x_train)[1]
#     num_iter = int((params['num_conv_layers'] - 1)/2)
    
#     input_img = Input(shape = (input_dim, 1))
#     x = Conv1D(params['num_filters'][0], params['kernel_size'],
#                activation=params['activation'], padding='same')(input_img)
#     for i in range(num_iter):
#         x = MaxPooling1D(2, padding='same')(x)
#         x = Dropout(params['dropout'])(x)
#         x = Conv1D(1, 1, activation='relu')(x)
#         # x = MaxPooling1D([params['num_filters'][i]],
#         #                  data_format='channels_first')(x)
#         x = Conv1D(params['num_filters'][1+i], params['kernel_size'],
#                    activation=params['activation'], padding='same')(x)
#     x = MaxPooling1D([params['num_filters'][i]], 
#                      data_format='channels_first')(x)
#     x = Flatten()(x)
#     encoded = Dense(params['latent_dim'], activation=params['activation'])(x)
#     # return encoded
#     encoder = Model(input_img, encoded)
#     return encoder
    
    # def normalize1(x):
#     xmin = np.min(x, axis=1, keepdims=True)
#     x = x - xmin
#     xmax = np.max(x, axis=1, keepdims=True)
#     x = x * 2 / xmax
#     x = x - 1.
#     # scale = 2/(xmax-xmin)
#     # offset = (xmin - xmax)/(xmax-xmin)
#     # x = x*scale + offset
#     return x
    
    
