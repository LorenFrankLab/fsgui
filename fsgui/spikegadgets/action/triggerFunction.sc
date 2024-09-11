int f22go
int f22PulseCounter = 1
int f22TrainCounter = 1;

int f22LockOut = 0;

function 22
  if (f22LockOut == 0) do
    f22LockOut = 1
    f22go = 1
    f22PulseCounter = 1
    f22TrainCounter = 1
    if f22go == 1 do
        while f22go == 1 && f22PulseCounter <= 20 do every 5
          portout[4]=1
          do in 2
            portout[4]=0
          end
          f22PulseCounter = f22PulseCounter + 1
        then do
          f22PulseCounter = 1
          f22TrainCounter = f22TrainCounter + 1
        end
    end
    f22LockOut = 0
  end
end;


function 23
  f22go = 0
  portout[4]=0
end;